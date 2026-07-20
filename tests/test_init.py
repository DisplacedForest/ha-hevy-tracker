from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hevy.api import HevyApiClient
from custom_components.hevy.const import CONF_API_KEY, DOMAIN


def _sample_workout() -> dict:
    return {
        "id": "w1",
        "title": "Push Day",
        "routine_id": "r1",
        "start_time": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "end_time": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "exercises": [
            {
                "title": "Bench Press",
                "exercise_template_id": "t1",
                "sets": [{"type": "normal", "weight_kg": 60, "reps": 10}],
            }
        ],
    }


def _patch_api():
    return patch.multiple(
        HevyApiClient,
        get_workout_count=AsyncMock(return_value=42),
        get_workouts=AsyncMock(
            return_value={"workouts": [_sample_workout()], "page_count": 1}
        ),
        get_workout_events=AsyncMock(return_value={"events": []}),
        get_exercise_templates=AsyncMock(
            return_value={
                "exercise_templates": [
                    {
                        "id": "t1",
                        "title": "Bench Press",
                        "primary_muscle_group": "chest",
                        "secondary_muscle_groups": [],
                        "equipment": "barbell",
                        "type": "weight_reps",
                    }
                ],
                "page_count": 1,
            }
        ),
        get_routines=AsyncMock(
            return_value={
                "routines": [
                    {
                        "id": "r1",
                        "title": "Push Day",
                        "exercises": [{"title": "Bench Press"}],
                    }
                ]
            }
        ),
    )


async def test_setup_creates_entities_and_unloads(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_key"},
        options={},
    )
    entry.add_to_hass(hass)

    with _patch_api():
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.entry_id in hass.data[DOMAIN]

    sensor_states = [
        s for s in hass.states.async_all() if s.entity_id.startswith("sensor.")
    ]
    assert sensor_states

    workout_count = next(
        (
            s
            for s in sensor_states
            if s.entity_id.endswith("workout_count")
            and "weekly" not in s.entity_id
        ),
        None,
    )
    assert workout_count is not None
    assert workout_count.state == "42"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
