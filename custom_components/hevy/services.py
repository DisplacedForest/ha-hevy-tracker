"""Service handlers for the Hevy Workout Tracker integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import HevyApiError
from .const import (
    DOMAIN,
    KG_TO_LBS,
    METERS_TO_KM,
    METERS_TO_MILES,
    UNIT_SYSTEM_METRIC,
)
from .coordinator import HevyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_WORKOUT_HISTORY = "get_workout_history"
SERVICE_LOG_WORKOUT = "log_workout"

SET_TYPES = ["warmup", "normal", "failure", "dropset"]
RPE_VALUES = [6.0, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
MEASUREMENT_FIELDS = ("weight", "reps", "duration_seconds", "distance")
MAX_NAME_SUGGESTIONS = 3

WORKOUT_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("days", default=30): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=90)
        ),
    }
)


def _set_has_measurement(value: dict[str, Any]) -> dict[str, Any]:
    if not any(value.get(field) is not None for field in MEASUREMENT_FIELDS):
        raise vol.Invalid(
            "Each set needs at least one of weight, reps, duration_seconds, "
            "or distance"
        )
    return value


SET_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("type", default="normal"): vol.In(SET_TYPES),
            vol.Optional("weight"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("reps"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Optional("duration_seconds"): vol.All(
                vol.Coerce(int), vol.Range(min=0)
            ),
            vol.Optional("distance"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("rpe"): vol.All(vol.Coerce(float), vol.In(RPE_VALUES)),
        }
    ),
    _set_has_measurement,
)

EXERCISE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Required("sets"): vol.All(
            cv.ensure_list, vol.Length(min=1), [SET_SCHEMA]
        ),
    }
)

LOG_WORKOUT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("title"): cv.string,
        vol.Required("exercises"): vol.All(
            cv.ensure_list, vol.Length(min=1), [EXERCISE_SCHEMA]
        ),
        vol.Optional("start_time"): cv.datetime,
        vol.Optional("end_time"): cv.datetime,
        vol.Optional("duration_minutes"): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("description"): cv.string,
        vol.Optional("is_private", default=False): cv.boolean,
    }
)


def _to_kg(
    coordinator: HevyDataUpdateCoordinator, weight: float | None
) -> float | None:
    if weight is None:
        return None
    if coordinator.unit_system == UNIT_SYSTEM_METRIC:
        return float(weight)
    return round(weight / KG_TO_LBS, 2)


def _to_meters(
    coordinator: HevyDataUpdateCoordinator, distance: float | None
) -> int | None:
    if distance is None:
        return None
    if coordinator.unit_system == UNIT_SYSTEM_METRIC:
        return round(distance / METERS_TO_KM)
    return round(distance / METERS_TO_MILES)


def _resolve_template_id(
    coordinator: HevyDataUpdateCoordinator, name: str
) -> str:
    templates = coordinator.exercise_templates

    for template_id, template in templates.items():
        if template.get("title") == name:
            return template_id

    lowered = name.lower()
    for template_id, template in templates.items():
        title = template.get("title")
        if title and title.lower() == lowered:
            return template_id

    near_misses: list[str] = []
    for template in templates.values():
        title = template.get("title")
        if title and lowered in title.lower():
            near_misses.append(title)
        if len(near_misses) == MAX_NAME_SUGGESTIONS:
            break

    message = f"Exercise '{name}' was not found in the Hevy exercise catalog"
    if near_misses:
        message = f"{message}. Did you mean: {', '.join(near_misses)}?"
    raise HomeAssistantError(message)


def async_register_services(hass: HomeAssistant) -> None:
    """Register Hevy services."""

    async def handle_get_workout_history(call: ServiceCall) -> ServiceResponse:
        """Handle the get_workout_history service call."""
        days = call.data.get("days", 30)
        config_entry_id = call.data["config_entry_id"]

        if config_entry_id not in hass.data.get(DOMAIN, {}):
            raise ServiceValidationError(f"Config entry {config_entry_id} not found")

        coordinator: HevyDataUpdateCoordinator = hass.data[DOMAIN][config_entry_id]
        cutoff = dt_util.now() - timedelta(days=days)

        # Filter workout history to requested window
        filtered_workouts: list[dict[str, Any]] = []
        for workout in coordinator._workout_history:
            start_time = workout.get("start_time")
            if start_time:
                try:
                    workout_dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                    if workout_dt > cutoff:
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
                    day_str = dt_util.as_local(
                        datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
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
                if template_id and template_id in coordinator.exercise_templates:
                    template = coordinator.exercise_templates[template_id]
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

    async def handle_log_workout(call: ServiceCall) -> ServiceResponse:
        """Handle the log_workout service call."""
        config_entry_id = call.data["config_entry_id"]

        if config_entry_id not in hass.data.get(DOMAIN, {}):
            raise ServiceValidationError(f"Config entry {config_entry_id} not found")

        coordinator: HevyDataUpdateCoordinator = hass.data[DOMAIN][config_entry_id]

        exercises_payload: list[dict[str, Any]] = []
        for exercise in call.data["exercises"]:
            template_id = _resolve_template_id(coordinator, exercise["name"])

            sets_payload: list[dict[str, Any]] = []
            for set_data in exercise["sets"]:
                sets_payload.append({
                    "type": set_data["type"],
                    "weight_kg": _to_kg(coordinator, set_data.get("weight")),
                    "reps": set_data.get("reps"),
                    "distance_meters": _to_meters(
                        coordinator, set_data.get("distance")
                    ),
                    "duration_seconds": set_data.get("duration_seconds"),
                    "rpe": set_data.get("rpe"),
                })

            exercises_payload.append({
                "exercise_template_id": template_id,
                "notes": exercise.get("notes"),
                "sets": sets_payload,
            })

        end_time = call.data.get("end_time") or dt_util.now()
        start_time = call.data.get("start_time")
        if start_time is None:
            duration_minutes = call.data.get("duration_minutes")
            start_time = (
                end_time - timedelta(minutes=duration_minutes)
                if duration_minutes
                else end_time
            )

        workout: dict[str, Any] = {"title": call.data["title"]}
        description = call.data.get("description")
        if description is not None:
            workout["description"] = description
        workout["is_private"] = call.data["is_private"]
        workout["start_time"] = start_time.isoformat()
        workout["end_time"] = end_time.isoformat()
        workout["exercises"] = exercises_payload

        try:
            created = await coordinator.client.create_workout({"workout": workout})
        except HevyApiError as err:
            raise HomeAssistantError(str(err)) from err

        await coordinator.async_request_refresh()

        result = created.get("workout", created) if created else {}
        if isinstance(result, list):
            result = result[0] if result else {}
        _LOGGER.debug("Logged workout %s", result.get("id"))

        return {
            "workout_id": result.get("id"),
            "title": result.get("title"),
        }

    if not hass.services.has_service(DOMAIN, SERVICE_GET_WORKOUT_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_WORKOUT_HISTORY,
            handle_get_workout_history,
            schema=WORKOUT_HISTORY_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_LOG_WORKOUT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_LOG_WORKOUT,
            handle_log_workout,
            schema=LOG_WORKOUT_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Hevy services if no more config entries."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_GET_WORKOUT_HISTORY)
        hass.services.async_remove(DOMAIN, SERVICE_LOG_WORKOUT)
