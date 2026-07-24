"""Tests for the Hevy calendar platform."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from custom_components.hevy.calendar import (
    HevyCalendarEntity,
    _build_event_description,
    _parse_dt,
    _workout_to_event,
)
from custom_components.hevy.const import UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_entry() -> MagicMock:
    """Return a mock config entry."""
    entry = MagicMock()
    entry.data = {"api_key": "test_key_123"}
    return entry


@pytest.fixture
def coordinator_imperial() -> MagicMock:
    """Return a mock coordinator with imperial unit system."""
    coord = MagicMock()
    coord.unit_system = UNIT_SYSTEM_IMPERIAL
    coord._get_weight_unit.return_value = "lbs"
    # Imperial: 60 kg -> 132.5 lbs (60 * 2.20462 = 132.2772, rounded to 132.5)
    coord._convert_weight.side_effect = lambda kg: round(kg * 2.20462 * 2) / 2 if kg is not None else None
    return coord


@pytest.fixture
def coordinator_metric() -> MagicMock:
    """Return a mock coordinator with metric unit system."""
    coord = MagicMock()
    coord.unit_system = UNIT_SYSTEM_METRIC
    coord._get_weight_unit.return_value = "kg"
    # Metric: round kg to nearest 0.5
    coord._convert_weight.side_effect = lambda kg: round(kg * 2) / 2 if kg is not None else None
    return coord


@pytest.fixture
def sample_workouts() -> list[dict]:
    """Return sample workout data (most-recent-first, as coordinator stores)."""
    return [
        {
            "id": "w1",
            "title": "Push Day",
            "start_time": "2026-07-17T10:30:00Z",
            "end_time": "2026-07-17T11:15:00Z",
            "exercises": [
                {
                    "title": "Bench Press",
                    "sets": [
                        {"weight_kg": 60, "reps": 10},
                        {"weight_kg": 60, "reps": 8},
                    ],
                },
            ],
        },
        {
            "id": "w2",
            "title": "Pull Day",
            "start_time": "2026-07-15T08:00:00Z",
            "end_time": "2026-07-15T09:00:00Z",
            "exercises": [
                {
                    "title": "Deadlift",
                    "sets": [{"weight_kg": 100, "reps": 5}],
                },
            ],
        },
        {
            "id": "w3",
            "title": "Leg Day",
            "start_time": "2026-07-10T07:00:00Z",
            "end_time": "2026-07-10T08:30:00Z",
            "exercises": [
                {
                    "title": "Squat",
                    "sets": [{"weight_kg": 80, "reps": 8}],
                },
            ],
        },
    ]


@pytest.fixture
def coordinator_with_data(
    sample_workouts: list[dict],
    coordinator_imperial: MagicMock,
) -> MagicMock:
    """Return a mock coordinator populated with sample workouts."""
    coordinator_imperial.data = {"workouts": sample_workouts}
    return coordinator_imperial


@pytest.fixture
def entity(
    coordinator_with_data: MagicMock,
    mock_entry: MagicMock,
) -> HevyCalendarEntity:
    """Return a HevyCalendarEntity with sample data."""
    return HevyCalendarEntity(coordinator_with_data, mock_entry)


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------

class TestParseDt:
    """Tests for _parse_dt."""

    def test_valid_iso(self) -> None:
        dt = _parse_dt("2026-07-17T10:30:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 7
        assert dt.day == 17
        assert dt.tzinfo is not None

    def test_none_input(self) -> None:
        assert _parse_dt(None) is None

    def test_empty_string(self) -> None:
        assert _parse_dt("") is None

    def test_invalid_string(self) -> None:
        assert _parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# _build_event_description
# ---------------------------------------------------------------------------

class TestBuildEventDescription:
    """Tests for _build_event_description."""

    def test_weighted_exercises_imperial(
        self, coordinator_imperial: MagicMock
    ) -> None:
        workout = {
            "exercises": [
                {
                    "title": "Bench Press",
                    "sets": [
                        {"weight_kg": 60, "reps": 10},
                        {"weight_kg": 60, "reps": 8},
                    ],
                },
            ],
        }
        desc = _build_event_description(workout, coordinator_imperial)
        assert desc is not None
        assert "Bench Press" in desc
        # 60kg -> 132.5 lbs; 132.5 * 10 + 132.5 * 8 = 2385.0
        assert "2385.0 lbs volume" in desc

    def test_weighted_exercises_metric(
        self, coordinator_metric: MagicMock
    ) -> None:
        workout = {
            "exercises": [
                {
                    "title": "Bench Press",
                    "sets": [
                        {"weight_kg": 60, "reps": 10},
                        {"weight_kg": 60, "reps": 8},
                    ],
                },
            ],
        }
        desc = _build_event_description(workout, coordinator_metric)
        assert desc is not None
        assert "Bench Press" in desc
        # 60kg rounded to 60.0; 60.0 * 10 + 60.0 * 8 = 1080.0
        assert "1080.0 kg volume" in desc

    def test_bodyweight_exercises(
        self, coordinator_imperial: MagicMock
    ) -> None:
        workout = {
            "exercises": [
                {"title": "Push-ups", "sets": [{"weight_kg": None, "reps": 20}]},
            ],
        }
        desc = _build_event_description(workout, coordinator_imperial)
        assert desc is not None
        assert "Push-ups" in desc
        assert "1 sets" in desc
        assert "lbs volume" not in desc

    def test_empty_exercises(
        self, coordinator_imperial: MagicMock
    ) -> None:
        assert _build_event_description({"exercises": []}, coordinator_imperial) is None

    def test_no_exercises_key(
        self, coordinator_imperial: MagicMock
    ) -> None:
        assert _build_event_description({}, coordinator_imperial) is None


# ---------------------------------------------------------------------------
# _workout_to_event
# ---------------------------------------------------------------------------

class TestWorkoutToEvent:
    """Tests for _workout_to_event."""

    def test_full_workout(self, coordinator_imperial: MagicMock) -> None:
        workout = {
            "id": "abc123",
            "title": "Push Day",
            "start_time": "2026-07-17T10:30:00Z",
            "end_time": "2026-07-17T11:15:00Z",
            "exercises": [
                {"title": "Bench Press", "sets": [{"weight_kg": 60, "reps": 10}]},
            ],
        }
        event = _workout_to_event(workout, coordinator_imperial)
        assert event is not None
        assert event.summary == "Push Day"
        assert event.start.year == 2026
        assert event.end.hour == 11
        assert event.uid == "abc123"
        assert event.description is not None
        assert "Bench Press" in event.description

    def test_missing_end_time_defaults_to_1hr(
        self, coordinator_imperial: MagicMock
    ) -> None:
        workout = {
            "id": "xyz",
            "title": "Leg Day",
            "start_time": "2026-07-15T08:00:00Z",
        }
        event = _workout_to_event(workout, coordinator_imperial)
        assert event is not None
        duration = event.end - event.start
        assert duration == timedelta(hours=1)

    def test_missing_start_time(
        self, coordinator_imperial: MagicMock
    ) -> None:
        assert _workout_to_event({"title": "No Time"}, coordinator_imperial) is None

    def test_fallback_title(
        self, coordinator_imperial: MagicMock
    ) -> None:
        workout = {"start_time": "2026-07-17T10:30:00Z"}
        event = _workout_to_event(workout, coordinator_imperial)
        assert event is not None
        assert event.summary == "Workout"

    def test_invalid_start_time(
        self, coordinator_imperial: MagicMock
    ) -> None:
        assert _workout_to_event({"start_time": "bad"}, coordinator_imperial) is None


# ---------------------------------------------------------------------------
# HevyCalendarEntity
# ---------------------------------------------------------------------------

class TestHevyCalendarEntityEvent:
    """Tests for HevyCalendarEntity.event property."""

    def test_event_returns_most_recent(
        self, entity: HevyCalendarEntity
    ) -> None:
        event = entity.event
        assert event is not None
        assert event.summary == "Push Day"
        assert event.uid == "w1"

    def test_event_no_data(self, mock_entry: MagicMock, coordinator_imperial: MagicMock) -> None:
        coordinator_imperial.data = None
        entity = HevyCalendarEntity(coordinator_imperial, mock_entry)
        assert entity.event is None

    def test_event_empty_workouts(self, mock_entry: MagicMock, coordinator_imperial: MagicMock) -> None:
        coordinator_imperial.data = {"workouts": []}
        entity = HevyCalendarEntity(coordinator_imperial, mock_entry)
        assert entity.event is None


@pytest.mark.asyncio
class TestHevyCalendarEntityGetEvents:
    """Tests for HevyCalendarEntity.async_get_events."""

    async def test_get_events_full_range(self, entity: HevyCalendarEntity) -> None:
        events = await entity.async_get_events(
            None,
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        assert len(events) == 3
        # Should be sorted oldest-first
        assert events[0].summary == "Leg Day"
        assert events[1].summary == "Pull Day"
        assert events[2].summary == "Push Day"

    async def test_get_events_narrow_range(
        self, entity: HevyCalendarEntity
    ) -> None:
        events = await entity.async_get_events(
            None,
            datetime(2026, 7, 14, tzinfo=timezone.utc),
            datetime(2026, 7, 16, tzinfo=timezone.utc),
        )
        assert len(events) == 1
        assert events[0].summary == "Pull Day"

    async def test_get_events_overlap_includes_crossing_event(
        self, mock_entry: MagicMock, coordinator_imperial: MagicMock
    ) -> None:
        """An event that starts before the range but ends inside it should be included."""
        workouts = [
            {
                "id": "crossing",
                "title": "Late Night Workout",
                "start_time": "2026-07-13T23:00:00Z",
                "end_time": "2026-07-14T01:00:00Z",
                "exercises": [],
            },
        ]
        coordinator_imperial.data = {"workouts": workouts}
        entity = HevyCalendarEntity(coordinator_imperial, mock_entry)
        events = await entity.async_get_events(
            None,
            datetime(2026, 7, 14, tzinfo=timezone.utc),
            datetime(2026, 7, 16, tzinfo=timezone.utc),
        )
        assert len(events) == 1
        assert events[0].summary == "Late Night Workout"

    async def test_get_events_empty_range(
        self, entity: HevyCalendarEntity
    ) -> None:
        events = await entity.async_get_events(
            None,
            datetime(2026, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        assert len(events) == 0

    async def test_get_events_no_data(self, mock_entry: MagicMock, coordinator_imperial: MagicMock) -> None:
        coordinator_imperial.data = None
        entity = HevyCalendarEntity(coordinator_imperial, mock_entry)
        events = await entity.async_get_events(
            None,
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        assert len(events) == 0

    async def test_get_events_skips_missing_start_time(
        self, mock_entry: MagicMock, coordinator_imperial: MagicMock
    ) -> None:
        workouts = [
            {"id": "bad", "title": "No Time", "exercises": []},
            {
                "id": "w1",
                "title": "Push Day",
                "start_time": "2026-07-17T10:30:00Z",
                "end_time": "2026-07-17T11:15:00Z",
                "exercises": [],
            },
        ]
        coordinator_imperial.data = {"workouts": workouts}
        entity = HevyCalendarEntity(coordinator_imperial, mock_entry)
        events = await entity.async_get_events(
            None,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        assert len(events) == 1
        assert events[0].summary == "Push Day"
