"""Service handlers for the Hevy Workout Tracker integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import HevyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_WORKOUT_HISTORY = "get_workout_history"

WORKOUT_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("days", default=30): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=90)
        ),
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register Hevy services."""

    async def handle_get_workout_history(call: ServiceCall) -> ServiceResponse:
        """Handle the get_workout_history service call."""
        days = call.data.get("days", 30)
        config_entry_id = call.data["config_entry_id"]

        if config_entry_id not in hass.data.get(DOMAIN, {}):
            raise ValueError(f"Config entry {config_entry_id} not found")

        coordinator: HevyDataUpdateCoordinator = hass.data[DOMAIN][config_entry_id]
        cutoff = datetime.now() - timedelta(days=days)

        # Filter workout history to requested window
        filtered_workouts: list[dict[str, Any]] = []
        for workout in coordinator._workout_history:
            start_time = workout.get("start_time")
            if start_time:
                try:
                    workout_dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                    if workout_dt.replace(tzinfo=None) >= cutoff:
                        filtered_workouts.append(workout)
                except (ValueError, AttributeError):
                    continue

        # Build enriched response
        workouts_response: list[dict[str, Any]] = []
        total_volume = 0.0
        total_duration = 0.0
        workout_days: list[str] = []

        for workout in filtered_workouts:
            start_time = workout.get("start_time")
            end_time = workout.get("end_time")
            duration_minutes = None

            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                    end_dt = datetime.fromisoformat(
                        end_time.replace("Z", "+00:00")
                    )
                    duration_minutes = round(
                        (end_dt - start_dt).total_seconds() / 60, 1
                    )
                    total_duration += duration_minutes
                except (ValueError, AttributeError):
                    pass

            if start_time:
                try:
                    day_str = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d")
                    if day_str not in workout_days:
                        workout_days.append(day_str)
                except (ValueError, AttributeError):
                    pass

            workout_volume = coordinator._calculate_total_volume(workout)
            total_volume += workout_volume

            # Collect muscle groups from exercises
            muscle_groups: list[str] = []
            seen_groups: set[str] = set()

            # Build exercises array
            exercises_response: list[dict[str, Any]] = []
            for exercise in workout.get("exercises", []):
                template_id = exercise.get("exercise_template_id")
                muscle_group = None
                if template_id and template_id in coordinator._exercise_templates:
                    template = coordinator._exercise_templates[template_id]
                    muscle_group = template.get("muscle_group")
                    if muscle_group and muscle_group not in seen_groups:
                        muscle_groups.append(muscle_group)
                        seen_groups.add(muscle_group)

                sets = exercise.get("sets", [])
                sets_converted: list[dict[str, Any]] = []
                ex_total_reps = 0

                for set_data in sets:
                    weight = coordinator._convert_weight(set_data.get("weight_kg"))
                    reps = set_data.get("reps")
                    sets_converted.append({
                        "type": set_data.get("type", "normal"),
                        "weight": weight,
                        "weight_unit": coordinator._get_weight_unit(),
                        "reps": reps,
                        "duration_seconds": set_data.get("duration_seconds"),
                    })
                    if reps:
                        ex_total_reps += reps

                exercises_response.append({
                    "name": exercise.get("title", "Unknown"),
                    "muscle_group": muscle_group,
                    "sets": sets_converted,
                    "best_set": coordinator._get_best_set_string(sets),
                    "total_reps": ex_total_reps if ex_total_reps > 0 else None,
                    "notes": exercise.get("notes"),
                })

            workouts_response.append({
                "id": workout.get("id"),
                "title": workout.get("title"),
                "date": start_time,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration_minutes,
                "total_volume": workout_volume,
                "routine_id": workout.get("routine_id"),
                "muscle_groups": muscle_groups,
                "exercises": exercises_response,
            })

        num_workouts = len(workouts_response)
        summary = {
            "total_workouts": num_workouts,
            "total_volume": round(total_volume, 1),
            "workout_days": workout_days,
            "avg_duration_minutes": (
                round(total_duration / num_workouts, 1) if num_workouts > 0 else 0
            ),
            "avg_volume_per_workout": (
                round(total_volume / num_workouts, 1) if num_workouts > 0 else 0
            ),
        }

        return {
            "summary": summary,
            "workouts": workouts_response,
        }

    if not hass.services.has_service(DOMAIN, SERVICE_GET_WORKOUT_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_WORKOUT_HISTORY,
            handle_get_workout_history,
            schema=WORKOUT_HISTORY_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Hevy services if no more config entries."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_GET_WORKOUT_HISTORY)
