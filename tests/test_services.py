from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from custom_components.hevy.api import HevyApiClient, HevyApiError, HevyAuthError
from custom_components.hevy.const import DOMAIN
from custom_components.hevy.services import (
    SERVICE_LOG_WORKOUT,
    async_register_services,
)

ENTRY_ID = "entry_1"

TEMPLATES = {
    "t1": {"title": "Bench Press", "muscle_group": "chest"},
    "t2": {"title": "Incline Bench Press", "muscle_group": "chest"},
    "t3": {"title": "Running", "muscle_group": "cardio"},
    "t4": {"title": "Close Grip Bench Press", "muscle_group": "triceps"},
}


def _register(hass, coordinator):
    coordinator._exercise_templates = dict(TEMPLATES)
    coordinator.client.create_workout = AsyncMock(
        return_value={"id": "w-123", "title": "Push Day"}
    )
    coordinator.async_request_refresh = AsyncMock()
    hass.data.setdefault(DOMAIN, {})[ENTRY_ID] = coordinator
    async_register_services(hass)
    return coordinator


@pytest.fixture
async def imperial_setup(hass, imperial_coordinator):
    return _register(hass, imperial_coordinator)


@pytest.fixture
async def metric_setup(hass, metric_coordinator):
    return _register(hass, metric_coordinator)


def _call_data(**overrides):
    data = {
        "config_entry_id": ENTRY_ID,
        "title": "Push Day",
        "exercises": [
            {
                "name": "Bench Press",
                "sets": [{"type": "normal", "weight": 225, "reps": 5}],
            }
        ],
        "start_time": "2026-08-20T17:00:00+00:00",
        "end_time": "2026-08-20T18:00:00+00:00",
    }
    data.update(overrides)
    return data


async def _log(hass, **overrides):
    return await hass.services.async_call(
        DOMAIN,
        SERVICE_LOG_WORKOUT,
        _call_data(**overrides),
        blocking=True,
        return_response=True,
    )


class TestSchema:
    async def test_service_is_registered(self, hass, imperial_setup) -> None:
        assert hass.services.has_service(DOMAIN, SERVICE_LOG_WORKOUT)

    async def test_missing_title(self, hass, imperial_setup) -> None:
        data = _call_data()
        del data["title"]
        with pytest.raises(vol.Invalid):
            await hass.services.async_call(
                DOMAIN, SERVICE_LOG_WORKOUT, data, blocking=True
            )

    async def test_empty_exercises(self, hass, imperial_setup) -> None:
        with pytest.raises(vol.Invalid):
            await _log(hass, exercises=[])

    async def test_empty_sets(self, hass, imperial_setup) -> None:
        with pytest.raises(vol.Invalid):
            await _log(hass, exercises=[{"name": "Bench Press", "sets": []}])

    async def test_set_without_measurement(self, hass, imperial_setup) -> None:
        with pytest.raises(vol.Invalid):
            await _log(
                hass,
                exercises=[{"name": "Bench Press", "sets": [{"type": "normal"}]}],
            )

    async def test_bad_set_type(self, hass, imperial_setup) -> None:
        with pytest.raises(vol.Invalid):
            await _log(
                hass,
                exercises=[
                    {"name": "Bench Press", "sets": [{"type": "cooldown", "reps": 5}]}
                ],
            )

    async def test_bad_rpe(self, hass, imperial_setup) -> None:
        with pytest.raises(vol.Invalid):
            await _log(
                hass,
                exercises=[
                    {"name": "Bench Press", "sets": [{"reps": 5, "rpe": 8.2}]}
                ],
            )

    async def test_valid_rpe_accepted(self, hass, imperial_setup) -> None:
        await _log(
            hass,
            exercises=[{"name": "Bench Press", "sets": [{"reps": 5, "rpe": 8.5}]}],
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["sets"][0]["rpe"] == 8.5


class TestNameResolution:
    async def test_exact_match(self, hass, imperial_setup) -> None:
        await _log(hass)
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["exercise_template_id"] == "t1"

    async def test_case_insensitive_match(self, hass, imperial_setup) -> None:
        await _log(
            hass,
            exercises=[{"name": "bench PRESS", "sets": [{"reps": 5}]}],
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["exercise_template_id"] == "t1"

    async def test_unknown_exercise_lists_suggestions(
        self, hass, imperial_setup
    ) -> None:
        with pytest.raises(HomeAssistantError) as err:
            await _log(
                hass,
                exercises=[{"name": "bench press machine", "sets": [{"reps": 5}]}],
            )
        message = str(err.value)
        assert "bench press machine" in message
        with pytest.raises(HomeAssistantError) as err:
            await _log(
                hass,
                exercises=[{"name": "Bench", "sets": [{"reps": 5}]}],
            )
        message = str(err.value)
        assert "Bench Press" in message
        assert message.count(",") <= 2

    async def test_nothing_posted_on_miss(self, hass, imperial_setup) -> None:
        with pytest.raises(HomeAssistantError):
            await _log(
                hass,
                exercises=[
                    {"name": "Bench Press", "sets": [{"reps": 5}]},
                    {"name": "Nonexistent Lift", "sets": [{"reps": 5}]},
                ],
            )
        imperial_setup.client.create_workout.assert_not_awaited()
        imperial_setup.async_request_refresh.assert_not_awaited()


class TestConversion:
    async def test_imperial_weight_to_kg(self, hass, imperial_setup) -> None:
        await _log(hass)
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["sets"][0]["weight_kg"] == 102.06

    async def test_metric_weight_passthrough(self, hass, metric_setup) -> None:
        await _log(
            hass,
            exercises=[
                {"name": "Bench Press", "sets": [{"weight": 102.5, "reps": 5}]}
            ],
        )
        payload = metric_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["sets"][0]["weight_kg"] == 102.5

    async def test_imperial_distance_to_meters(self, hass, imperial_setup) -> None:
        await _log(
            hass,
            exercises=[
                {
                    "name": "Running",
                    "sets": [{"distance": 3.1, "duration_seconds": 1500}],
                }
            ],
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["sets"][0]["distance_meters"] == 4989

    async def test_metric_distance_to_meters(self, hass, metric_setup) -> None:
        await _log(
            hass,
            exercises=[{"name": "Running", "sets": [{"distance": 5.0}]}],
        )
        payload = metric_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["exercises"][0]["sets"][0]["distance_meters"] == 5000


class TestPayload:
    async def test_full_payload_shape(self, hass, imperial_setup) -> None:
        await _log(
            hass,
            description="Felt strong",
            is_private=True,
            exercises=[
                {
                    "name": "Bench Press",
                    "notes": "Paused reps",
                    "sets": [
                        {"type": "warmup", "weight": 135, "reps": 8},
                        {"weight": 225, "reps": 5, "rpe": 9},
                    ],
                },
                {
                    "name": "Running",
                    "sets": [{"distance": 3.1, "duration_seconds": 1500}],
                },
            ],
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload == {
            "workout": {
                "title": "Push Day",
                "description": "Felt strong",
                "is_private": True,
                "start_time": "2026-08-20T17:00:00+00:00",
                "end_time": "2026-08-20T18:00:00+00:00",
                "exercises": [
                    {
                        "exercise_template_id": "t1",
                        "notes": "Paused reps",
                        "sets": [
                            {
                                "type": "warmup",
                                "weight_kg": 61.24,
                                "reps": 8,
                                "distance_meters": None,
                                "duration_seconds": None,
                                "rpe": None,
                            },
                            {
                                "type": "normal",
                                "weight_kg": 102.06,
                                "reps": 5,
                                "distance_meters": None,
                                "duration_seconds": None,
                                "rpe": 9,
                            },
                        ],
                    },
                    {
                        "exercise_template_id": "t3",
                        "notes": None,
                        "sets": [
                            {
                                "type": "normal",
                                "weight_kg": None,
                                "reps": None,
                                "distance_meters": 4989,
                                "duration_seconds": 1500,
                                "rpe": None,
                            }
                        ],
                    },
                ],
            }
        }

    async def test_description_omitted_when_absent(
        self, hass, imperial_setup
    ) -> None:
        await _log(hass)
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert "description" not in payload["workout"]
        assert payload["workout"]["is_private"] is False

    async def test_duration_minutes_derives_start_time(
        self, hass, imperial_setup
    ) -> None:
        data = _call_data(duration_minutes=45)
        del data["start_time"]
        await hass.services.async_call(
            DOMAIN, SERVICE_LOG_WORKOUT, data, blocking=True, return_response=True
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["start_time"] == "2026-08-20T17:15:00+00:00"
        assert payload["workout"]["end_time"] == "2026-08-20T18:00:00+00:00"

    async def test_defaults_to_now(self, hass, imperial_setup) -> None:
        data = _call_data()
        del data["start_time"]
        del data["end_time"]
        await hass.services.async_call(
            DOMAIN, SERVICE_LOG_WORKOUT, data, blocking=True, return_response=True
        )
        payload = imperial_setup.client.create_workout.await_args.args[0]
        assert payload["workout"]["start_time"] == payload["workout"]["end_time"]
        assert payload["workout"]["end_time"]


class TestResponseAndErrors:
    async def test_returns_workout_id_and_title(self, hass, imperial_setup) -> None:
        response = await _log(hass)
        assert response == {"workout_id": "w-123", "title": "Push Day"}

    async def test_handles_nested_workout_response(
        self, hass, imperial_setup
    ) -> None:
        imperial_setup.client.create_workout = AsyncMock(
            return_value={"workout": {"id": "w-9", "title": "Leg Day"}}
        )
        response = await _log(hass)
        assert response == {"workout_id": "w-9", "title": "Leg Day"}

    async def test_refresh_requested_after_success(
        self, hass, imperial_setup
    ) -> None:
        await _log(hass)
        imperial_setup.async_request_refresh.assert_awaited_once()

    async def test_api_error_wrapped(self, hass, imperial_setup) -> None:
        imperial_setup.client.create_workout = AsyncMock(
            side_effect=HevyApiError("boom")
        )
        with pytest.raises(HomeAssistantError) as err:
            await _log(hass)
        assert "boom" in str(err.value)
        imperial_setup.async_request_refresh.assert_not_awaited()

    async def test_auth_error_wrapped(self, hass, imperial_setup) -> None:
        imperial_setup.client.create_workout = AsyncMock(
            side_effect=HevyAuthError("Invalid API key")
        )
        with pytest.raises(HomeAssistantError) as err:
            await _log(hass)
        assert "Invalid API key" in str(err.value)

    async def test_unknown_config_entry(self, hass, imperial_setup) -> None:
        with pytest.raises(ValueError):
            await _log(hass, config_entry_id="missing")


class TestApiClient:
    async def test_create_workout_posts_json(self) -> None:
        client = HevyApiClient("key")
        client._request = AsyncMock(return_value={"id": "w-1"})
        workout = {"workout": {"title": "Push Day"}}

        assert await client.create_workout(workout) == {"id": "w-1"}
        assert client._request.await_args.args == ("POST", "/workouts")
        assert client._request.await_args.kwargs == {"json": workout}
