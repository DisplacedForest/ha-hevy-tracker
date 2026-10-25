from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from conftest import body_day, paged_body_measurements
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hevy.api import HevyApiClient
from custom_components.hevy.const import (
    BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE,
    CONF_API_KEY,
    CONF_UNIT_SYSTEM,
    DOMAIN,
    MAX_BODY_MEASUREMENT_PAGES,
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


def _patch_api(body_measurements: dict | Callable[..., Any] | None = None):
    get_body_measurements = (
        AsyncMock(side_effect=body_measurements)
        if callable(body_measurements)
        else AsyncMock(
            return_value=body_measurements or {"body_measurements": [], "page_count": 1}
        )
    )
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
        get_body_measurements=get_body_measurements,
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


def _weights(count: int, first: int = 0) -> list[dict]:
    return [
        {"date": body_day(first + offset), "weight_kg": 80.0} for offset in range(count)
    ]


async def _setup_metric(hass, body_measurements) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_key"},
        options={CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC},
    )
    entry.add_to_hass(hass)
    with _patch_api(body_measurements):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _waist(hass):
    return next(
        (s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_waist")),
        None,
    )


async def test_body_measurement_older_than_first_50_entries_on_fresh_setup(
    hass,
) -> None:
    waists = [
        {"date": body_day(50), "waist": 81},
        {"date": body_day(60), "waist": 83},
    ]
    await _setup_metric(hass, paged_body_measurements([*_weights(50), *waists]))

    waist = _waist(hass)
    assert waist is not None
    assert float(waist.state) == 81
    assert waist.attributes["measured_on"] == body_day(50)
    assert waist.attributes["previous_value"] == 83
    assert waist.attributes["previous_measured_on"] == body_day(60)
    assert waist.attributes["change"] == -2


async def test_body_measurement_kept_after_leaving_first_50_entries(hass) -> None:
    waists = [
        {"date": body_day(50), "waist": 81},
        {"date": body_day(60), "waist": 83},
    ]
    entry = await _setup_metric(hass, paged_body_measurements([*_weights(5), *waists]))

    newer = [{"date": body_day(-offset), "weight_kg": 79.0} for offset in range(1, 51)]
    pages = AsyncMock(
        side_effect=paged_body_measurements([*newer, *_weights(5), *waists])
    )
    with _patch_api(), patch.object(HevyApiClient, "get_body_measurements", pages):
        await hass.data[DOMAIN][entry.entry_id].async_refresh()
        await hass.async_block_till_done()

    assert pages.call_count == 5
    waist = _waist(hass)
    assert waist is not None
    assert waist.state != "unavailable"
    assert float(waist.state) == 81
    assert waist.attributes["previous_value"] == 83
    assert waist.attributes["change"] == -2


async def _refresh(hass, entry, get_body_measurements: AsyncMock) -> None:
    with (
        _patch_api(),
        patch.object(HevyApiClient, "get_body_measurements", get_body_measurements),
    ):
        await hass.data[DOMAIN][entry.entry_id].async_refresh()
        await hass.async_block_till_done()


async def test_deleted_newest_body_measurement_disappears_on_next_update(
    hass,
) -> None:
    entries = [
        {"date": body_day(0), "weight_kg": 79.0},
        *_weights(59, first=1),
    ]
    entry = await _setup_metric(hass, paged_body_measurements(entries))
    assert float(_body_state(hass, "_body_weight").state) == 79.0

    pages = AsyncMock(side_effect=paged_body_measurements(entries[1:]))
    await _refresh(hass, entry, pages)

    assert pages.call_count == MAX_BODY_MEASUREMENT_PAGES
    weight = _body_state(hass, "_body_weight")
    assert float(weight.state) == 80.0
    assert weight.attributes["measured_on"] == body_day(1)
    assert _body_state(hass, "_last_body_measurement").state == body_day(1)


async def test_invalid_body_measurement_response_keeps_all_sensors(hass) -> None:
    entry = await _setup_metric(hass, BODY_MEASUREMENTS)

    pages = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "<html>", 0))
    await _refresh(hass, entry, pages)

    assert pages.called
    assert hass.data[DOMAIN][entry.entry_id].last_update_success
    workout_count = _body_state(hass, "_workout_count")
    assert workout_count.state == "42"
    assert float(_body_state(hass, "_body_weight").state) == 78.5
    assert float(_body_state(hass, "_waist").state) == 81
    assert _body_state(hass, "_last_body_measurement").state == "2026-03-09"


@pytest.mark.parametrize("measurements", [False, {}, "", None, 0])
async def test_falsey_body_measurement_response_keeps_all_sensors(
    hass, measurements
) -> None:
    entry = await _setup_metric(hass, BODY_MEASUREMENTS)

    pages = AsyncMock(return_value={"body_measurements": measurements, "page_count": 1})
    await _refresh(hass, entry, pages)

    assert pages.called
    assert _body_state(hass, "_workout_count").state == "42"
    assert float(_body_state(hass, "_body_weight").state) == 78.5
    assert float(_body_state(hass, "_waist").state) == 81
    assert _body_state(hass, "_last_body_measurement").state == "2026-03-09"


async def test_body_measurement_beyond_long_history_on_fresh_setup(hass) -> None:
    entries = [*_weights(2000), {"date": body_day(2000), "waist": 83}]
    pages = AsyncMock(side_effect=paged_body_measurements(entries))
    entry = await _setup_metric(hass, pages)
    assert pages.call_count == BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE
    assert _waist(hass) is None

    for _ in range(20):
        pages.reset_mock()
        await _refresh(hass, entry, pages)
        assert pages.call_count <= (
            MAX_BODY_MEASUREMENT_PAGES + BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE
        )
        if _waist(hass) is not None:
            break

    waist = _waist(hass)
    assert waist is not None
    assert float(waist.state) == 83
    assert waist.attributes["measured_on"] == body_day(2000)


async def _switch_unit_system(hass, entry, unit_system: str) -> None:
    with _patch_api(BODY_MEASUREMENTS):
        hass.config_entries.async_update_entry(
            entry, options={CONF_UNIT_SYSTEM: unit_system}
        )
        await hass.async_block_till_done()


def _body_state(hass, suffix: str):
    return next(
        s for s in hass.states.async_all("sensor") if s.entity_id.endswith(suffix)
    )


async def test_switching_unit_system_updates_existing_body_sensors(hass) -> None:
    entry = await _setup_metric(hass, BODY_MEASUREMENTS)
    assert _body_state(hass, "_waist").attributes["unit_of_measurement"] == "cm"

    await _switch_unit_system(hass, entry, UNIT_SYSTEM_IMPERIAL)
    waist = _body_state(hass, "_waist")
    weight = _body_state(hass, "_body_weight")
    assert waist.attributes["unit_of_measurement"] == "in"
    assert round(float(waist.state), 1) == 31.9
    assert weight.attributes["unit_of_measurement"] == "lb"
    assert round(float(weight.state), 1) == 173.1
    assert weight.attributes["previous_value"] == 176.37
    assert weight.attributes["change"] == -3.31

    await _switch_unit_system(hass, entry, UNIT_SYSTEM_METRIC)
    waist = _body_state(hass, "_waist")
    weight = _body_state(hass, "_body_weight")
    assert waist.attributes["unit_of_measurement"] == "cm"
    assert float(waist.state) == 81
    assert weight.attributes["unit_of_measurement"] == "kg"
    assert float(weight.state) == 78.5
    assert weight.attributes["previous_value"] == 80.0
    assert weight.attributes["change"] == -1.5


async def test_explicit_body_sensor_unit_survives_unit_system_switch(hass) -> None:
    entry = await _setup_metric(hass, BODY_MEASUREMENTS)
    registry = er.async_get(hass)
    for suffix, unit in (("_body_weight", "g"), ("_waist", "mm")):
        registry.async_update_entity_options(
            _body_state(hass, suffix).entity_id,
            "sensor",
            {"unit_of_measurement": unit},
        )
    await hass.async_block_till_done()

    for unit_system in (UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC, UNIT_SYSTEM_IMPERIAL):
        await _switch_unit_system(hass, entry, unit_system)
        weight = _body_state(hass, "_body_weight")
        waist = _body_state(hass, "_waist")
        assert weight.attributes["unit_of_measurement"] == "g"
        assert float(weight.state) == 78500
        assert weight.attributes["previous_value"] == 80000
        assert weight.attributes["change"] == -1500
        assert waist.attributes["unit_of_measurement"] == "mm"
        assert float(waist.state) == 810
