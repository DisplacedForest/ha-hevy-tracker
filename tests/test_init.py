from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hevy.api import HevyApiClient
from custom_components.hevy.const import (
    CONF_API_KEY,
    CONF_UNIT_SYSTEM,
    DOMAIN,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_SYSTEM_METRIC,
)


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


BODY_MEASUREMENTS = {
    "page": 1,
    "page_count": 1,
    "body_measurements": [
        {"date": "2026-03-09", "weight_kg": 78.5, "waist": None},
        {"date": "2026-03-02", "weight_kg": 80.0, "fat_percent": 18.0, "waist": 81},
    ],
}


def _patch_api(body_measurements: dict | None = None):
    return patch.multiple(
        HevyApiClient,
        get_user_info=AsyncMock(return_value={"data": {"name": "Test account"}}),
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
        get_body_measurements=AsyncMock(
            return_value=body_measurements or {"body_measurements": [], "page_count": 1}
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
            if s.entity_id.endswith("workout_count") and "weekly" not in s.entity_id
        ),
        None,
    )
    assert workout_count is not None
    assert workout_count.state == "42"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_body_measurement_sensors(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_key"},
        options={CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC},
    )
    entry.add_to_hass(hass)

    with _patch_api(BODY_MEASUREMENTS):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all("sensor")}

    def find(suffix: str):
        return next(s for e, s in states.items() if e.endswith(suffix))

    weight = find("_body_weight")
    assert float(weight.state) == 78.5
    assert weight.attributes["unit_of_measurement"] == "kg"
    assert weight.attributes["measured_on"] == "2026-03-09"
    assert weight.attributes["change"] == -1.5

    waist = find("_waist")
    assert float(waist.state) == 81
    assert waist.attributes["unit_of_measurement"] == "cm"
    assert waist.attributes["measured_on"] == "2026-03-02"

    assert float(find("_body_fat").state) == 18.0
    assert find("_last_body_measurement").state == "2026-03-09"
    assert not [e for e in states if e.endswith("_left_calf")]


async def test_body_measurement_sensors_imperial(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_key"},
        options={CONF_UNIT_SYSTEM: UNIT_SYSTEM_IMPERIAL},
    )
    entry.add_to_hass(hass)

    with _patch_api(BODY_MEASUREMENTS):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all("sensor")}
    waist = next(s for e, s in states.items() if e.endswith("_waist"))
    assert waist.attributes["unit_of_measurement"] == "in"
    assert round(float(waist.state), 1) == 31.9

    weight = next(s for e, s in states.items() if e.endswith("_body_weight"))
    assert weight.attributes["unit_of_measurement"] == "lb"
    assert weight.attributes["previous_value"] == 176.37
    assert weight.attributes["change"] == -3.31


async def test_body_measurement_sensor_added_when_field_first_logged(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_key"},
        options={CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC},
    )
    entry.add_to_hass(hass)

    with _patch_api(BODY_MEASUREMENTS):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    def body_sensors():
        return sorted(
            s.entity_id
            for s in hass.states.async_all("sensor")
            if s.entity_id.endswith(("_body_weight", "_neck"))
        )

    assert len(body_sensors()) == 1

    later = {
        "page": 1,
        "page_count": 1,
        "body_measurements": [
            {"date": "2026-03-16", "weight_kg": 78.0, "neck_cm": 36},
            *BODY_MEASUREMENTS["body_measurements"],
        ],
    }
    with _patch_api(later):
        await hass.data[DOMAIN][entry.entry_id].async_refresh()
        await hass.async_block_till_done()

    assert len(body_sensors()) == 2
    neck = next(
        s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_neck")
    )
    assert float(neck.state) == 36
    assert neck.attributes["measured_on"] == "2026-03-16"
