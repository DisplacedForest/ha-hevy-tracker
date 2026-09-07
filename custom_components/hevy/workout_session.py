from __future__ import annotations

import asyncio
import logging
import math
from copy import deepcopy
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import KG_TO_LBS, METERS_TO_KM, METERS_TO_MILES
from .coordinator import HevyDataUpdateCoordinator
from .services import RPE_VALUES, SET_TYPES
from .session_store import SessionStore

_LOGGER = logging.getLogger(__name__)


def finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise vol.Invalid("Enter a number")
    if not math.isfinite(value) or value < 0 or value > 1000000:
        raise vol.Invalid("Enter a finite number between 0 and 1000000")
    return float(value)


def whole_number(value: Any) -> int:
    number = finite_number(value)
    if not number.is_integer():
        raise vol.Invalid("Enter a whole number")
    return int(number)


TITLE = vol.All(str, vol.Length(min=1, max=200))
SESSION_SET_SCHEMA = vol.Schema(
    {
        vol.Optional("type", default="normal"): vol.In(SET_TYPES),
        vol.Optional("weight"): finite_number,
        vol.Optional("reps"): whole_number,
        vol.Optional("duration_seconds"): whole_number,
        vol.Optional("distance"): finite_number,
        vol.Optional("rpe"): vol.All(finite_number, vol.In(RPE_VALUES)),
        vol.Optional("completed", default=False): bool,
    }
)
SESSION_EXERCISES_SCHEMA = vol.All(
    list,
    vol.Length(max=100),
    [
        vol.Schema(
            {
                vol.Required("exercise_template_id"): TITLE,
                vol.Required("name"): TITLE,
                vol.Optional("notes", default=""): vol.All(str, vol.Length(max=2000)),
                vol.Required("sets"): vol.All(
                    list, vol.Length(min=1, max=100), [SESSION_SET_SCHEMA]
                ),
            }
        )
    ],
)


def routine_exercises(coordinator: HevyDataUpdateCoordinator, routine: dict) -> list:
    exercises = []
    for exercise in routine.get("exercises", []):
        sets = []
        for original in exercise.get("sets", []):
            item = {"type": original.get("type", "normal"), "completed": False}
            for field in ("reps", "duration_seconds", "rpe"):
                if original.get(field) is not None:
                    item[field] = original[field]
            weight = coordinator._convert_weight(original.get("weight_kg"))
            distance = coordinator._convert_distance(original.get("distance_meters"))
            if weight is not None:
                item["weight"] = weight
            if distance is not None:
                item["distance"] = distance
            sets.append(item)
        exercises.append(
            {
                "exercise_template_id": exercise.get("exercise_template_id"),
                "name": exercise.get("name"),
                "notes": exercise.get("notes") or "",
                "sets": sets or [{"type": "normal", "completed": False}],
            }
        )
    return exercises


class WorkoutSession:
    def __init__(
        self, hass: HomeAssistant, entry_id: str, coordinator: HevyDataUpdateCoordinator
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.store = SessionStore(hass, entry_id)
        self.session: dict[str, Any] | None = None
        self.lock = asyncio.Lock()
        self.closed = False

    async def load(self) -> None:
        saved = await self.store.async_load()
        self.session = saved.get("session") if saved else None
        if self.session and self.session["status"] == "submitting":
            recovered = deepcopy(self.session)
            recovered["status"] = "uncertain"
            recovered["revision"] += 1
            await self._save(recovered)

    async def close(self) -> None:
        async with self.lock:
            self.closed = True

    def snapshot(self) -> dict[str, Any] | None:
        return deepcopy(self.session)

    async def _save(self, session: dict[str, Any] | None) -> None:
        save = asyncio.create_task(self.store.async_save({"session": session}))
        cancelled = False
        while not save.done():
            try:
                await asyncio.shield(save)
            except asyncio.CancelledError:
                cancelled = True
        save.result()
        self.session = session
        if cancelled:
            raise asyncio.CancelledError

    def _current(self, session_id: str, revision: int) -> dict[str, Any]:
        if self.closed:
            raise ServiceValidationError(
                "This Hevy integration is unloading. Reconnect."
            )
        if not self.session or self.session["id"] != session_id:
            raise ServiceValidationError(
                "This workout is no longer current. Reload it."
            )
        if self.session["revision"] != revision:
            raise ServiceValidationError(
                "This workout changed on another device. Reload it."
            )
        return deepcopy(self.session)

    def _exercises(self, exercises: list) -> list:
        try:
            result = SESSION_EXERCISES_SCHEMA(exercises)
        except vol.Invalid as err:
            raise ServiceValidationError(str(err)) from err
        for exercise in result:
            template = self.coordinator.exercise_templates.get(
                exercise["exercise_template_id"]
            )
            if not template:
                raise ServiceValidationError(
                    "An exercise is missing from the Hevy catalog."
                )
            exercise["name"] = template["title"]
            for item in exercise["sets"]:
                if item["completed"] and not any(
                    item.get(field) is not None
                    for field in ("weight", "reps", "duration_seconds", "distance")
                ):
                    raise ServiceValidationError(
                        "Enter a measurement before checking a set."
                    )
        return result

    async def start(
        self, routine_id: str | None, title: str | None, is_private: bool = False
    ) -> dict:
        async with self.lock:
            if self.closed or self.session:
                raise ServiceValidationError(
                    "Resume or clear the current workout first."
                )
            routine = None
            if routine_id:
                routine = next(
                    (r for r in self.coordinator.routines if r["id"] == routine_id),
                    None,
                )
                if routine is None:
                    raise ServiceValidationError("This routine is no longer available.")
            session = {
                "id": uuid4().hex,
                "revision": 1,
                "status": "active",
                "title": (
                    title or (routine["title"] if routine else "Workout")
                ).strip(),
                "start_time": dt_util.utcnow().isoformat(),
                "weight_unit": self.coordinator._get_weight_unit(),
                "distance_unit": self.coordinator._get_distance_unit(),
                "is_private": is_private,
                "exercises": self._exercises(
                    routine_exercises(self.coordinator, routine) if routine else []
                ),
            }
            if not session["title"]:
                raise ServiceValidationError("Enter a workout title.")
            await self._save(session)
            return deepcopy(session)

    async def update(self, session_id: str, revision: int, data: dict) -> dict:
        async with self.lock:
            session = self._current(session_id, revision)
            if session["status"] != "active":
                raise ServiceValidationError("This workout cannot be edited now.")
            title = data["title"].strip()
            if not title:
                raise ServiceValidationError("Enter a workout title.")
            session.update(
                title=title,
                is_private=data["is_private"],
                exercises=self._exercises(data["exercises"]),
                revision=revision + 1,
            )
            await self._save(session)
            return deepcopy(session)

    def _payload(self, session: dict) -> dict:
        exercises = []
        metric = session["weight_unit"] == "kg"
        for exercise in session["exercises"]:
            sets = []
            for item in exercise["sets"]:
                if not item["completed"]:
                    continue
                weight = item.get("weight")
                distance = item.get("distance")
                sets.append(
                    {
                        "type": item["type"],
                        "weight_kg": (
                            weight
                            if metric or weight is None
                            else round(weight / KG_TO_LBS, 2)
                        ),
                        "reps": item.get("reps"),
                        "duration_seconds": item.get("duration_seconds"),
                        "distance_meters": (
                            round(
                                distance / (METERS_TO_KM if metric else METERS_TO_MILES)
                            )
                            if distance is not None
                            else None
                        ),
                        "rpe": item.get("rpe"),
                    }
                )
            if sets:
                exercises.append(
                    {
                        "exercise_template_id": exercise["exercise_template_id"],
                        "notes": exercise.get("notes") or None,
                        "sets": sets,
                    }
                )
        if not exercises:
            raise ServiceValidationError("Check off at least one completed set first.")
        return {
            "workout": {
                "title": session["title"],
                "is_private": session["is_private"],
                "start_time": session["start_time"],
                "end_time": session["end_time"],
                "exercises": exercises,
            }
        }

    async def finish(self, session_id: str, revision: int) -> dict:
        async with self.lock:
            if (
                self.session
                and self.session["id"] == session_id
                and self.session["status"] == "finished"
            ):
                return deepcopy(self.session)
            session = self._current(session_id, revision)
            if session["status"] != "active":
                raise ServiceValidationError(
                    "Check this workout in Hevy before continuing."
                )
            session["end_time"] = (
                session.get("end_time") or dt_util.utcnow().isoformat()
            )
            payload = self._payload(session)
            session.update(status="submitting", revision=revision + 1)
            try:
                await self._save(session)
            except asyncio.CancelledError:
                uncertain = deepcopy(session)
                uncertain.update(status="uncertain", revision=session["revision"] + 1)
                self.session = uncertain
                await self._save(uncertain)
                raise
            try:
                created = await self.coordinator.client.create_workout(payload)
                result = created.get("workout", created)
                if isinstance(result, list):
                    result = result[0] if len(result) == 1 else {}
                if (
                    not isinstance(result, dict)
                    or not isinstance(result.get("id"), str)
                    or not result["id"]
                ):
                    raise HomeAssistantError("Hevy did not return a workout ID.")
            except (Exception, asyncio.CancelledError) as err:
                uncertain = deepcopy(session)
                uncertain.update(status="uncertain", revision=session["revision"] + 1)
                self.session = uncertain
                await self._save(uncertain)
                if isinstance(err, asyncio.CancelledError):
                    raise
                raise HomeAssistantError(
                    "Submission could not be confirmed. Check Hevy before retrying."
                ) from err
            finished = deepcopy(session)
            finished.update(
                status="finished",
                workout_id=result["id"],
                revision=session["revision"] + 1,
            )
            self.session = finished
            await self._save(finished)
        try:
            await self.coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Workout saved, but the Hevy dashboard refresh failed")
        return deepcopy(finished)

    async def cancel(self, session_id: str, revision: int) -> None:
        async with self.lock:
            session = self._current(session_id, revision)
            if session["status"] not in ("active", "finished"):
                raise ServiceValidationError(
                    "Resolve this submission before clearing it."
                )
            await self._save(None)

    async def resolve(
        self, session_id: str, revision: int, resolution: str
    ) -> dict | None:
        async with self.lock:
            session = self._current(session_id, revision)
            if session["status"] != "uncertain":
                raise ServiceValidationError("This workout does not need recovery.")
            if resolution == "discard":
                await self._save(None)
                return None
            session.update(status="active", revision=revision + 1)
            await self._save(session)
            return deepcopy(session)
