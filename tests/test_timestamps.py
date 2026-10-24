from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.hevy.calendar import _parse_dt
from custom_components.hevy.const import DOMAIN
from custom_components.hevy.sensor import HevyLastWorkoutDateSensor
from custom_components.hevy.services import (
    SERVICE_GET_WORKOUT_HISTORY,
    async_register_services,
)


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        ("2026-07-17T01:30:00Z", datetime(2026, 7, 17, 1, 30, tzinfo=UTC)),
        ("2026-07-17T01:30:00+00:00", datetime(2026, 7, 17, 1, 30, tzinfo=UTC)),
        ("2026-07-16T18:30:00-07:00", datetime(2026, 7, 17, 1, 30, tzinfo=UTC)),
        ("2026-07-17T07:00:00+05:30", datetime(2026, 7, 17, 1, 30, tzinfo=UTC)),
        ("2026-07-17T01:30:00.123456Z", datetime(2026, 7, 17, 1, 30, 0, 123456, UTC)),
        ("2026-07-17T01:30:00", datetime(2026, 7, 17, 1, 30)),
        (None, None),
        ("", None),
        ("not-a-date", None),
        (42, None),
        ({"date": "2026-07-17"}, None),
        (["2026-07-17"], None),
    ],
)
def test_calendar_and_sensor_timestamp_parsing(timestamp, expected):
    coordinator = MagicMock(data={"last_workout_date": timestamp})
    entry = MagicMock(data={"api_key": "fixture-key"})
    sensor = HevyLastWorkoutDateSensor(coordinator, entry)
    assert _parse_dt(timestamp) == expected
    assert sensor.native_value == expected


@pytest.mark.parametrize(
    "start_time, end_time, count, duration",
    [
        ("2026-07-17T01:30:00Z", "2026-07-17T02:15:00Z", 1, 45.0),
        ("2026-07-17T01:30:00+00:00", "2026-07-17T02:15:00+00:00", 1, 45.0),
        ("2026-07-16T18:30:00-07:00", "2026-07-17T07:45:00+05:30", 1, 45.0),
        ("2026-07-17T01:30:00Z", 42, 1, None),
        (42, "2026-07-17T02:15:00Z", 0, None),
        ({"date": "2026-07-17"}, None, 0, None),
        ("not-a-date", "not-a-date", 0, None),
    ],
)
async def test_coordinator_and_history_preserve_local_dates_and_duration(
    hass,
    imperial_coordinator,
    mock_client,
    freezer,
    start_time,
    end_time,
    count,
    duration,
):
    freezer.move_to("2026-07-17T03:00:00Z")
    await hass.config.async_set_time_zone("America/Los_Angeles")
    workout = {
        "id": "timestamp-fixture",
        "title": "Evening workout",
        "start_time": start_time,
        "end_time": end_time,
        "exercises": [],
    }
    mock_client.get_workouts.return_value = {"workouts": [workout], "page_count": 1}
    data = await imperial_coordinator._async_update_data()
    expected_days = ["2026-07-16"] if count else []
    assert data["weekly_workout_count"] == count
    assert data["worked_out_today"] is bool(count)
    assert data["current_streak"] == count
    assert data["workout_dates"] == expected_days
    assert data["workout_duration_minutes"] == duration
    if count:
        assert data["workout_summaries"]["2026-07-16"]["duration_minutes"] == duration
    hass.data.setdefault(DOMAIN, {})["timestamp-entry"] = imperial_coordinator
    async_register_services(hass)
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_WORKOUT_HISTORY,
        {"config_entry_id": "timestamp-entry", "days": 30},
        blocking=True,
        return_response=True,
    )
    assert response["summary"]["total_workouts"] == count
    assert response["summary"]["workout_days"] == expected_days
    if count:
        assert response["workouts"][0]["duration_minutes"] == duration
