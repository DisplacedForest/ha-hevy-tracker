"""Data Update Coordinator for Hevy integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HevyApiClient, HevyApiError
from .const import DOMAIN, KG_TO_LBS, UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC

_LOGGER = logging.getLogger(__name__)


class HevyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Hevy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HevyApiClient,
        update_interval: timedelta,
        unit_system: str = UNIT_SYSTEM_IMPERIAL,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: Hevy API client
            update_interval: Update interval
            unit_system: Unit system (imperial or metric)
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.unit_system = unit_system
        self._workout_history: list[dict[str, Any]] = []
        self._exercise_prs: dict[str, dict[str, Any]] = {}

    def _convert_weight(self, weight_kg: float | None) -> float | None:
        """Convert weight based on unit system.

        Args:
            weight_kg: Weight in kilograms

        Returns:
            Weight in configured unit system, or None
        """
        if weight_kg is None:
            return None

        if self.unit_system == UNIT_SYSTEM_METRIC:
            # Round kg to nearest 0.5
            return round(weight_kg * 2) / 2
        else:
            # Convert to lbs and round to nearest 0.5
            weight_lbs = weight_kg * KG_TO_LBS
            return round(weight_lbs * 2) / 2

    def _get_weight_unit(self) -> str:
        """Get the weight unit string.

        Returns:
            Unit string (kg or lbs)
        """
        return "kg" if self.unit_system == UNIT_SYSTEM_METRIC else "lbs"

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string like "1m 30s" or "45s"
        """
        if seconds is None:
            return "0s"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if minutes > 0:
            return f"{minutes}m {remaining_seconds:02d}s"
        return f"{seconds}s"

    def _get_best_set_string(self, sets: list[dict[str, Any]]) -> str:
        """Get the best set as a formatted string.

        Args:
            sets: List of set dictionaries

        Returns:
            Formatted string like "35 lbs × 12" or "60s"
        """
        if not sets:
            return "No sets"

        # Check if this is a timed exercise
        first_set = sets[0]
        if first_set.get("duration_seconds") is not None:
            max_duration = max(
                (s.get("duration_seconds", 0) for s in sets), default=0
            )
            return self._format_duration(max_duration)

        # For weighted exercises, find heaviest weight with most reps
        best_set = max(
            sets,
            key=lambda s: (s.get("weight_kg", 0), s.get("reps", 0)),
            default=sets[0],
        )
        weight = self._convert_weight(best_set.get("weight_kg"))
        reps = best_set.get("reps", 0)
        unit = self._get_weight_unit()

        if weight is not None and reps:
            return f"{weight} {unit} × {reps}"
        if weight is not None:
            return f"{weight} {unit}"
        if reps:
            return f"{reps} reps"
        return "No data"

    def _calculate_total_volume(self, workout: dict[str, Any]) -> float:
        """Calculate total volume (weight × reps) for a workout.

        Args:
            workout: Workout dictionary

        Returns:
            Total volume in configured unit system
        """
        total_volume = 0.0
        for exercise in workout.get("exercises", []):
            for set_data in exercise.get("sets", []):
                weight_kg = set_data.get("weight_kg")
                reps = set_data.get("reps")
                if weight_kg is not None and reps is not None:
                    weight = self._convert_weight(weight_kg)
                    if weight:
                        total_volume += weight * reps
        return round(total_volume, 1)

    def _update_exercise_prs(self, workouts: list[dict[str, Any]]) -> None:
        """Update exercise personal records from workout history.

        Args:
            workouts: List of workout dictionaries
        """
        for workout in workouts:
            for exercise in workout.get("exercises", []):
                exercise_title = exercise.get("title", "").lower()
                template_id = exercise.get("exercise_template_id")

                if not exercise_title:
                    continue

                # Track PR for weighted exercises (always store in kg for consistency)
                for set_data in exercise.get("sets", []):
                    weight_kg = set_data.get("weight_kg")
                    reps = set_data.get("reps", 0)

                    if weight_kg is not None:
                        if exercise_title not in self._exercise_prs:
                            self._exercise_prs[exercise_title] = {
                                "weight_kg": weight_kg,
                                "reps": reps,
                                "template_id": template_id,
                            }
                        else:
                            current_pr = self._exercise_prs[exercise_title]
                            # Update if heavier weight, or same weight with more reps
                            if (
                                weight_kg > current_pr["weight_kg"]
                                or (
                                    weight_kg == current_pr["weight_kg"]
                                    and reps > current_pr["reps"]
                                )
                            ):
                                self._exercise_prs[exercise_title] = {
                                    "weight_kg": weight_kg,
                                    "reps": reps,
                                    "template_id": template_id,
                                }

    def _calculate_current_streak(self, workouts: list[dict[str, Any]]) -> int:
        """Calculate current workout streak (consecutive days with workouts).

        Allows 1 rest day gap in A-B-C rotation.

        Args:
            workouts: List of workouts sorted by date (most recent first)

        Returns:
            Streak count in days
        """
        if not workouts:
            return 0

        # Get workout dates (just the date part, no time)
        workout_dates = set()
        for workout in workouts:
            start_time = workout.get("start_time")
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    workout_dates.add(dt.date())
                except (ValueError, AttributeError):
                    continue

        if not workout_dates:
            return 0

        sorted_dates = sorted(workout_dates, reverse=True)
        today = datetime.now().date()

        # Check if there's a workout today or yesterday
        if sorted_dates[0] not in (today, today - timedelta(days=1)):
            return 0

        streak = 0
        current_date = today
        last_workout_date = None

        for workout_date in sorted_dates:
            if last_workout_date is None:
                # First workout in the streak
                streak += (current_date - workout_date).days + 1
                last_workout_date = workout_date
            else:
                gap = (last_workout_date - workout_date).days
                if gap <= 2:  # Allow 1 rest day
                    streak += gap
                    last_workout_date = workout_date
                else:
                    break

        return streak

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Hevy API.

        Returns:
            Dict containing all processed workout data

        Raises:
            UpdateFailed: If update fails
        """
        try:
            # Fetch workout count
            workout_count = await self.client.get_workout_count()

            # Fetch recent workouts with full details (API limit: pageSize <= 10)
            workouts_data = await self.client.get_workouts(page=1, page_size=10)
            workouts = workouts_data.get("workouts", [])

            # Update workout history (keep last 10)
            self._workout_history = workouts[:10]

            # Update PRs from all fetched workouts
            self._update_exercise_prs(self._workout_history)

            # Process data for sensors
            last_workout = workouts[0] if workouts else None
            now = datetime.now()

            # Calculate weekly workout count
            week_ago = now - timedelta(days=7)
            weekly_count = 0
            for workout in workouts:
                start_time = workout.get("start_time")
                if start_time:
                    try:
                        workout_dt = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        if workout_dt.replace(tzinfo=None) >= week_ago:
                            weekly_count += 1
                    except (ValueError, AttributeError):
                        continue

            # Check if worked out today
            worked_out_today = False
            if last_workout:
                start_time = last_workout.get("start_time")
                if start_time:
                    try:
                        workout_dt = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        worked_out_today = workout_dt.date() == now.date()
                    except (ValueError, AttributeError):
                        pass

            # Process exercises from last workout
            exercises_summary = []
            if last_workout:
                for exercise in last_workout.get("exercises", []):
                    sets = exercise.get("sets", [])
                    exercise_title = exercise.get("title", "Unknown")

                    # Convert sets to configured unit system
                    sets_converted = []
                    total_reps = 0
                    total_duration = 0

                    for set_data in sets:
                        weight = self._convert_weight(set_data.get("weight_kg"))
                        reps = set_data.get("reps")
                        duration = set_data.get("duration_seconds")

                        set_info = {
                            "type": set_data.get("type", "normal"),
                            "weight": weight,
                            "weight_unit": self._get_weight_unit(),
                            "reps": reps,
                            "duration_seconds": duration,
                        }
                        sets_converted.append(set_info)

                        if reps:
                            total_reps += reps
                        if duration:
                            total_duration += duration

                    exercise_summary = {
                        "name": exercise_title,
                        "sets": sets_converted,
                        "best_set": self._get_best_set_string(sets),
                        "total_reps": total_reps if total_reps > 0 else None,
                        "total_duration_seconds": (
                            total_duration if total_duration > 0 else None
                        ),
                    }
                    exercises_summary.append(exercise_summary)

            # Calculate workout duration
            workout_duration_minutes = None
            if last_workout:
                start_time = last_workout.get("start_time")
                end_time = last_workout.get("end_time")
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                        duration = end_dt - start_dt
                        workout_duration_minutes = round(duration.total_seconds() / 60, 1)
                    except (ValueError, AttributeError):
                        pass

            # Build per-exercise data
            exercise_data = {}
            for workout in workouts:
                for exercise in workout.get("exercises", []):
                    exercise_title = exercise.get("title", "").lower()
                    if not exercise_title:
                        continue

                    sets = exercise.get("sets", [])
                    template_id = exercise.get("exercise_template_id")

                    # Convert sets
                    sets_converted = []
                    total_reps = 0
                    total_duration = 0
                    last_weight = None

                    for set_data in sets:
                        weight = self._convert_weight(set_data.get("weight_kg"))
                        reps = set_data.get("reps")
                        duration = set_data.get("duration_seconds")

                        sets_converted.append(
                            {
                                "type": set_data.get("type", "normal"),
                                "weight": weight,
                                "weight_unit": self._get_weight_unit(),
                                "reps": reps,
                                "duration_seconds": duration,
                            }
                        )

                        if weight:
                            last_weight = weight
                        if reps:
                            total_reps += reps
                        if duration:
                            total_duration += duration

                    # Only update if this is the most recent workout for this exercise
                    if exercise_title not in exercise_data:
                        pr_data = self._exercise_prs.get(exercise_title, {})
                        pr_weight = (
                            self._convert_weight(pr_data.get("weight_kg"))
                            if pr_data.get("weight_kg")
                            else None
                        )

                        exercise_data[exercise_title] = {
                            "display_name": exercise.get("title", "Unknown"),
                            "last_workout_date": workout.get("start_time"),
                            "last_workout_sets": sets_converted,
                            "weight": last_weight,
                            "weight_unit": self._get_weight_unit(),
                            "total_reps": total_reps if total_reps > 0 else None,
                            "total_sets": len(sets),
                            "exercise_template_id": template_id,
                            "personal_record_weight": pr_weight,
                            "personal_record_reps": pr_data.get("reps"),
                            "best_set": self._get_best_set_string(sets),
                            "total_duration_seconds": (
                                total_duration if total_duration > 0 else None
                            ),
                        }

            return {
                "workout_count": workout_count,
                "last_workout": last_workout,
                "last_workout_date": (
                    last_workout.get("start_time") if last_workout else None
                ),
                "last_workout_title": (
                    last_workout.get("title") if last_workout else None
                ),
                "workout_duration_minutes": workout_duration_minutes,
                "total_volume": (
                    self._calculate_total_volume(last_workout) if last_workout else 0
                ),
                "total_volume_unit": self._get_weight_unit(),
                "exercises_summary": exercises_summary,
                "weekly_workout_count": weekly_count,
                "worked_out_today": worked_out_today,
                "worked_out_this_week": weekly_count > 0,
                "current_streak": self._calculate_current_streak(workouts),
                "exercise_data": exercise_data,
                "workouts": workouts,
            }

        except HevyApiError as err:
            raise UpdateFailed(f"Error communicating with Hevy API: {err}") from err
