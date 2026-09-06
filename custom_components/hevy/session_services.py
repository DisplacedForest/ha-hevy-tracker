from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN
from .workout_session import (
    SESSION_EXERCISES_SCHEMA,
    TITLE,
    WorkoutSession,
    routine_exercises,
    whole_number,
)

SESSION_SERVICES = (
    "get_workout_board",
    "start_workout",
    "update_workout",
    "finish_workout",
    "cancel_workout",
    "resolve_workout",
)
ENTRY = {vol.Required("config_entry_id"): str}
CURRENT = {
    **ENTRY,
    vol.Required("session_id"): str,
    vol.Required("revision"): whole_number,
}


def register_session_services(hass: HomeAssistant) -> None:
    def manager(entry_id: str) -> WorkoutSession:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if coordinator is None or coordinator.workout_session is None:
            raise ServiceValidationError("Choose a loaded Hevy integration.")
        return coordinator.workout_session

    async def board(call: ServiceCall) -> dict[str, Any]:
        accounts = [
            {"config_entry_id": entry.entry_id, "title": entry.title}
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id in hass.data.get(DOMAIN, {})
        ]
        entry_id = call.data.get("config_entry_id")
        if entry_id is None and len(accounts) == 1:
            entry_id = accounts[0]["config_entry_id"]
        if entry_id is None:
            return {"accounts": accounts, "config_entry_id": None}
        current = manager(entry_id)
        coordinator = current.coordinator
        next_workout = (
            coordinator.data.get("routine_data", {}) if coordinator.data else {}
        )
        return {
            "accounts": accounts,
            "config_entry_id": entry_id,
            "weight_unit": coordinator._get_weight_unit(),
            "distance_unit": coordinator._get_distance_unit(),
            "routines": [
                {
                    "id": routine["id"],
                    "title": routine["title"],
                    "exercises": routine_exercises(coordinator, routine),
                }
                for routine in coordinator.routines
            ],
            "exercises": sorted(
                [
                    {
                        "id": template_id,
                        "title": template.get("title"),
                        "type": template.get("type"),
                        "muscle_group": template.get("muscle_group"),
                    }
                    for template_id, template in coordinator.exercise_templates.items()
                ],
                key=lambda item: item["title"] or "",
            ),
            "session": current.snapshot(),
            "next_routine_id": next_workout.get("routine_id"),
        }

    async def mutate(call: ServiceCall) -> dict[str, Any]:
        current = manager(call.data["config_entry_id"])
        if call.service == "start_workout":
            session = await current.start(
                call.data.get("routine_id"), call.data.get("title")
            )
        elif call.service == "update_workout":
            session = await current.update(
                call.data["session_id"], call.data["revision"], call.data
            )
        elif call.service == "finish_workout":
            session = await current.finish(
                call.data["session_id"], call.data["revision"]
            )
        elif call.service == "cancel_workout":
            await current.cancel(call.data["session_id"], call.data["revision"])
            session = None
        else:
            session = await current.resolve(
                call.data["session_id"], call.data["revision"], call.data["resolution"]
            )
        return {"session": session}

    schemas: dict[str, dict[Any, Any]] = {
        "get_workout_board": {vol.Optional("config_entry_id"): str},
        "start_workout": {
            **ENTRY,
            vol.Optional("routine_id"): TITLE,
            vol.Optional("title"): TITLE,
        },
        "update_workout": {
            **CURRENT,
            vol.Required("title"): TITLE,
            vol.Required("is_private"): bool,
            vol.Required("exercises"): SESSION_EXERCISES_SCHEMA,
        },
        "finish_workout": CURRENT,
        "cancel_workout": CURRENT,
        "resolve_workout": {
            **CURRENT,
            vol.Required("resolution"): vol.In(("retry", "discard")),
        },
    }
    for service, schema in schemas.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(
                DOMAIN,
                service,
                board if service == "get_workout_board" else mutate,
                schema=vol.Schema(schema),
                supports_response=SupportsResponse.ONLY,
            )


def unregister_session_services(hass: HomeAssistant) -> None:
    if not hass.data.get(DOMAIN):
        for service in SESSION_SERVICES:
            hass.services.async_remove(DOMAIN, service)
