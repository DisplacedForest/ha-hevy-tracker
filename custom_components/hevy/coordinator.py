"""Data Update Coordinator for Hevy integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HevyApiClient, HevyApiError
from .const import (
    DOMAIN,
    KG_TO_LBS,
    MAX_WORKOUT_PAGES,
    MUSCLE_DUE_THRESHOLD_DAYS,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_SYSTEM_METRIC,
    WORKOUT_HISTORY_DAYS,
)

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
        self._exercise_templates: dict[str, dict] = {}  # Cache templates by ID
        self._routines: list[dict[str, Any]] = []

    async def fetch_exercise_templates(self) -> None:
        """Fetch and cache exercise template catalog from all pages."""
        try:
            page = 1
            total_templates = 0

            while True:
                data = await self.client.get_exercise_templates(page=page, page_size=50)
                templates = data.get("exercise_templates", [])

                if not templates:
                    break  # No more templates

                for template in templates:
                    template_id = template.get("id")
                    if template_id:
                        self._exercise_templates[template_id] = {
                            "title": template.get("title"),
                            "muscle_group": template.get("primary_muscle_group"),
                            "secondary_muscle_groups": template.get(
                                "secondary_muscle_groups", []
                            ),
                            "equipment": template.get("equipment"),
                            "type": template.get("type"),
                        }
                        total_templates += 1

                # Check if there are more pages
                page_count = data.get("page_count", 1)
                if page >= page_count:
                    break

                page += 1

            _LOGGER.info(
                "Cached %d exercise templates from %d pages", total_templates, page
            )
        except Exception as err:
            _LOGGER.warning("Failed to fetch exercise templates: %s", err)

    async def fetch_routines(self) -> None:
        """Fetch and cache routines from the API."""
        try:
            data = await self.client.get_routines()
            routines = data.get("routines", [])
            self._routines = []
            for routine in routines:
                routine_id = routine.get("id")
                if routine_id:
                    exercises = []
                    for exercise in routine.get("exercises", []):
                        title = exercise.get("title")
                        if title:
                            exercises.append(title)
                    self._routines.append({
                        "id": routine_id,
                        "title": routine.get("title", "Untitled"),
                        "exercises": exercises,
                    })
            _LOGGER.info("Cached %d routines", len(self._routines))
        except Exception as err:
            _LOGGER.warning("Failed to fetch routines: %s", err)

    async def _fetch_30_day_workouts(self) -> list[dict[str, Any]]:
        """Fetch up to 30 days of workout history with pagination.

        Returns:
            List of workout dicts covering the last 30 days
        """
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=WORKOUT_HISTORY_DAYS)
        all_workouts: list[dict[str, Any]] = []

        for page in range(1, MAX_WORKOUT_PAGES + 1):
            data = await self.client.get_workouts(page=page, page_size=10)
            workouts = data.get("workouts", [])

            if not workouts:
                break

            reached_cutoff = False
            for workout in workouts:
                start_time = workout.get("start_time")
                if start_time:
                    try:
                        workout_dt = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        if workout_dt < cutoff:
                            reached_cutoff = True
                            break
                    except (ValueError, AttributeError):
                        pass
                all_workouts.append(workout)

            if reached_cutoff:
                break

            # Check if there are more pages
            page_count = data.get("page_count", 1)
            if page >= page_count:
                break

        return all_workouts

    def _detect_next_workout(self) -> dict[str, Any]:
        """Detect the next workout in the routine rotation.

        Returns:
            Dict with next routine info and rotation position
        """
        if not self._routines:
            return {
                "next_routine": "No routines configured",
                "routine_id": None,
                "routine_title": "No routines configured",
                "last_workout_title": None,
                "last_workout_routine_id": None,
                "rotation_position": None,
                "rotation_total": 0,
                "exercises_preview": [],
            }

        last_workout = self._workout_history[0] if self._workout_history else None
        if not last_workout:
            # No workouts, suggest first routine
            first = self._routines[0]
            return {
                "next_routine": first["title"],
                "routine_id": first["id"],
                "routine_title": first["title"],
                "last_workout_title": None,
                "last_workout_routine_id": None,
                "rotation_position": 1,
                "rotation_total": len(self._routines),
                "exercises_preview": first["exercises"],
            }

        last_routine_id = last_workout.get("routine_id")
        last_title = last_workout.get("title")

        # Try to find the last workout's routine by routine_id
        found_index = None
        if last_routine_id:
            for i, routine in enumerate(self._routines):
                if routine["id"] == last_routine_id:
                    found_index = i
                    break

        if found_index is None:
            return {
                "next_routine": "No routine detected for last workout",
                "routine_id": None,
                "routine_title": "No routine detected for last workout",
                "last_workout_title": last_title,
                "last_workout_routine_id": last_routine_id,
                "rotation_position": None,
                "rotation_total": len(self._routines),
                "exercises_preview": [],
            }

        next_index = (found_index + 1) % len(self._routines)
        next_routine = self._routines[next_index]

        return {
            "next_routine": next_routine["title"],
            "routine_id": next_routine["id"],
            "routine_title": next_routine["title"],
            "last_workout_title": last_title,
            "last_workout_routine_id": last_routine_id,
            "rotation_position": next_index + 1,
            "rotation_total": len(self._routines),
            "exercises_preview": next_routine["exercises"],
        }

    def _aggregate_muscle_groups(self) -> dict[str, Any]:
        """Aggregate muscle group data from workout history.

        Returns:
            Dict with muscle group tracking data
        """
        now = datetime.now(tz=timezone.utc)
        muscle_last_trained: dict[str, datetime] = {}
        last_workout_primary: list[str] = []
        last_workout_secondary: list[str] = []
        last_workout_date = None

        # Process all workouts for days_since_last tracking
        for workout in self._workout_history:
            start_time = workout.get("start_time")
            if not start_time:
                continue
            try:
                workout_dt = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                continue

            for exercise in workout.get("exercises", []):
                template_id = exercise.get("exercise_template_id")
                if not template_id or template_id not in self._exercise_templates:
                    continue

                template = self._exercise_templates[template_id]
                primary = template.get("muscle_group")
                secondaries = template.get("secondary_muscle_groups", [])

                if primary:
                    if primary not in muscle_last_trained or workout_dt > muscle_last_trained[primary]:
                        muscle_last_trained[primary] = workout_dt
                for sec in secondaries:
                    if sec not in muscle_last_trained or workout_dt > muscle_last_trained[sec]:
                        muscle_last_trained[sec] = workout_dt

        # Process last workout specifically for primary/secondary groups
        if self._workout_history:
            last_workout = self._workout_history[0]
            last_workout_date = last_workout.get("start_time")
            seen_primary = set()
            seen_secondary = set()

            for exercise in last_workout.get("exercises", []):
                template_id = exercise.get("exercise_template_id")
                if not template_id or template_id not in self._exercise_templates:
                    continue

                template = self._exercise_templates[template_id]
                primary = template.get("muscle_group")
                secondaries = template.get("secondary_muscle_groups", [])

                if primary and primary not in seen_primary:
                    last_workout_primary.append(primary)
                    seen_primary.add(primary)
                for sec in secondaries:
                    if sec not in seen_secondary:
                        last_workout_secondary.append(sec)
                        seen_secondary.add(sec)

        # Calculate days since last trained
        days_since_last: dict[str, int] = {}
        muscles_due: list[str] = []
        for group, last_dt in muscle_last_trained.items():
            days = (now - last_dt).days
            days_since_last[group] = days
            if days >= MUSCLE_DUE_THRESHOLD_DAYS:
                muscles_due.append(group)

        return {
            "last_workout_primary_groups": last_workout_primary,
            "last_workout_secondary_groups": last_workout_secondary,
            "last_workout_date": last_workout_date,
            "days_since_last": days_since_last,
            "muscles_due": sorted(muscles_due),
        }

    def _calculate_weekly_muscle_volume(self) -> dict[str, Any]:
        """Calculate volume per muscle group for the last 7 days.

        Returns:
            Dict with volume data per muscle group
        """
        now = datetime.now(tz=timezone.utc)
        week_ago = now - timedelta(days=7)

        volume_by_group: dict[str, float] = {}
        exercise_breakdown: dict[str, list[dict[str, Any]]] = {}
        total_volume = 0.0
        total_sets = 0
        total_workouts = 0

        for workout in self._workout_history:
            start_time = workout.get("start_time")
            if not start_time:
                continue
            try:
                workout_dt = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                continue

            if workout_dt < week_ago:
                continue

            total_workouts += 1

            for exercise in workout.get("exercises", []):
                template_id = exercise.get("exercise_template_id")
                if not template_id or template_id not in self._exercise_templates:
                    continue

                template = self._exercise_templates[template_id]
                muscle_group = template.get("muscle_group")
                if not muscle_group:
                    continue

                exercise_title = exercise.get("title", "Unknown")
                exercise_volume = 0.0
                exercise_sets = 0

                for set_data in exercise.get("sets", []):
                    # Skip warmup sets
                    set_type = set_data.get("type", "normal")
                    if set_type not in ("normal", "dropset", "failure"):
                        continue

                    weight_kg = set_data.get("weight_kg")
                    reps = set_data.get("reps")

                    # Skip bodyweight/timed exercises (no weight)
                    if weight_kg is None or reps is None:
                        continue

                    weight = self._convert_weight(weight_kg)
                    if weight:
                        set_volume = weight * reps
                        exercise_volume += set_volume
                        exercise_sets += 1

                if exercise_volume > 0:
                    volume_by_group[muscle_group] = volume_by_group.get(muscle_group, 0) + exercise_volume
                    total_volume += exercise_volume
                    total_sets += exercise_sets

                    if muscle_group not in exercise_breakdown:
                        exercise_breakdown[muscle_group] = []

                    # Check if exercise already in breakdown for this group
                    found = False
                    for entry in exercise_breakdown[muscle_group]:
                        if entry["exercise"] == exercise_title:
                            entry["volume"] = round(entry["volume"] + exercise_volume, 1)
                            entry["sets"] += exercise_sets
                            found = True
                            break
                    if not found:
                        exercise_breakdown[muscle_group].append({
                            "exercise": exercise_title,
                            "volume": round(exercise_volume, 1),
                            "sets": exercise_sets,
                        })

        # Round volume values
        rounded_groups = {k: round(v, 1) for k, v in volume_by_group.items()}

        return {
            "total_volume": round(total_volume, 1),
            "period_start": (now - timedelta(days=7)).isoformat(),
            "period_end": now.isoformat(),
            "total_sets": total_sets,
            "total_workouts": total_workouts,
            "muscle_groups": rounded_groups,
            "exercise_breakdown": exercise_breakdown,
        }

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

            # Fetch 30-day workout history with pagination
            workouts = await self._fetch_30_day_workouts()

            # Update workout history (full 30-day window)
            self._workout_history = workouts

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
                        "notes": exercise.get("notes"),
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
                            "notes": exercise.get("notes"),
                            "personal_record_weight": pr_weight,
                            "personal_record_reps": pr_data.get("reps"),
                            "best_set": self._get_best_set_string(sets),
                            "total_duration_seconds": (
                                total_duration if total_duration > 0 else None
                            ),
                        }

            # Build deduplicated, sorted list of workout dates (YYYY-MM-DD)
            workout_dates = set()
            for workout in workouts:
                start_time = workout.get("start_time")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        workout_dates.add(dt.strftime("%Y-%m-%d"))
                    except (ValueError, AttributeError):
                        continue
            workout_dates_sorted = sorted(workout_dates)

            # Build workout_summaries dict keyed by date string
            workout_summaries: dict[str, dict[str, Any]] = {}
            for workout in workouts:
                start_time = workout.get("start_time")
                end_time = workout.get("end_time")
                if not start_time:
                    continue
                try:
                    workout_dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                    date_key = workout_dt.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    continue

                # Skip if we already have an entry for this date (first = most recent)
                if date_key in workout_summaries:
                    continue

                # Calculate duration
                duration_minutes = None
                if end_time:
                    try:
                        end_dt = datetime.fromisoformat(
                            end_time.replace("Z", "+00:00")
                        )
                        duration_minutes = round(
                            (end_dt - workout_dt).total_seconds() / 60, 1
                        )
                    except (ValueError, AttributeError):
                        pass

                # Build exercises list
                summary_exercises: list[dict[str, Any]] = []
                for exercise in workout.get("exercises", []):
                    sets = exercise.get("sets", [])
                    sets_converted = []
                    total_reps = 0

                    for set_data in sets:
                        weight = self._convert_weight(set_data.get("weight_kg"))
                        reps = set_data.get("reps")
                        sets_converted.append({
                            "type": set_data.get("type", "normal"),
                            "weight": weight,
                            "weight_unit": self._get_weight_unit(),
                            "reps": reps,
                        })
                        if reps:
                            total_reps += reps

                    summary_exercises.append({
                        "name": exercise.get("title", "Unknown"),
                        "sets": sets_converted,
                        "best_set": self._get_best_set_string(sets),
                        "total_reps": total_reps if total_reps > 0 else None,
                        "notes": exercise.get("notes"),
                    })

                workout_summaries[date_key] = {
                    "title": workout.get("title", "Untitled"),
                    "duration_minutes": duration_minutes,
                    "total_volume": self._calculate_total_volume(workout),
                    "total_volume_unit": self._get_weight_unit(),
                    "exercise_count": len(summary_exercises),
                    "exercises": summary_exercises,
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
                "routine_data": self._detect_next_workout(),
                "muscle_group_data": self._aggregate_muscle_groups(),
                "weekly_muscle_volume": self._calculate_weekly_muscle_volume(),
                "workout_dates": workout_dates_sorted,
                "workout_summaries": workout_summaries,
            }

        except HevyApiError as err:
            raise UpdateFailed(f"Error communicating with Hevy API: {err}") from err
