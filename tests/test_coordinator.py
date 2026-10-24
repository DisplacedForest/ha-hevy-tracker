from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from conftest import body_day, paged_body_measurements
from homeassistant.util import dt as dt_util

from custom_components.hevy.api import HevyApiError, HevyNotFoundError
from custom_components.hevy.const import (
    BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE,
    MAX_BODY_MEASUREMENT_PAGES,
)


def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


class TestConvertWeight:
    async def test_none(self, imperial_coordinator) -> None:
        assert imperial_coordinator._convert_weight(None) is None

    async def test_imperial_converts_to_lbs(self, imperial_coordinator) -> None:
        assert imperial_coordinator._convert_weight(100) == 220.5

    async def test_imperial_rounds_to_half(self, imperial_coordinator) -> None:
        assert imperial_coordinator._convert_weight(60) == 132.5

    async def test_metric_keeps_kg(self, metric_coordinator) -> None:
        assert metric_coordinator._convert_weight(100) == 100.0

    async def test_metric_rounds_to_half(self, metric_coordinator) -> None:
        assert metric_coordinator._convert_weight(60.3) == 60.5
        assert metric_coordinator._convert_weight(60.2) == 60.0


class TestUnits:
    async def test_weight_unit(self, imperial_coordinator, metric_coordinator) -> None:
        assert imperial_coordinator._get_weight_unit() == "lbs"
        assert metric_coordinator._get_weight_unit() == "kg"

    async def test_distance_unit(
        self, imperial_coordinator, metric_coordinator
    ) -> None:
        assert imperial_coordinator._get_distance_unit() == "mi"
        assert metric_coordinator._get_distance_unit() == "km"


class TestConvertDistance:
    async def test_none(self, imperial_coordinator) -> None:
        assert imperial_coordinator._convert_distance(None) is None

    async def test_imperial_converts_to_miles(self, imperial_coordinator) -> None:
        assert imperial_coordinator._convert_distance(5000) == 3.11

    async def test_metric_converts_to_km(self, metric_coordinator) -> None:
        assert metric_coordinator._convert_distance(5000) == 5.0


class TestFormatDuration:
    async def test_none(self, imperial_coordinator) -> None:
        assert imperial_coordinator._format_duration(None) == "0s"

    async def test_seconds_only(self, imperial_coordinator) -> None:
        assert imperial_coordinator._format_duration(45) == "45s"

    async def test_minutes_and_seconds(self, imperial_coordinator) -> None:
        assert imperial_coordinator._format_duration(90) == "1m 30s"

    async def test_zero_padded_seconds(self, imperial_coordinator) -> None:
        assert imperial_coordinator._format_duration(60) == "1m 00s"


class TestGetBestSetString:
    async def test_empty(self, imperial_coordinator) -> None:
        assert imperial_coordinator._get_best_set_string([]) == "No sets"

    async def test_weighted_picks_heaviest(self, imperial_coordinator) -> None:
        sets = [
            {"weight_kg": 80, "reps": 10},
            {"weight_kg": 100, "reps": 5},
        ]
        assert imperial_coordinator._get_best_set_string(sets) == "220.5 lbs × 5"

    async def test_weighted_metric(self, metric_coordinator) -> None:
        sets = [{"weight_kg": 100, "reps": 5}]
        assert metric_coordinator._get_best_set_string(sets) == "100.0 kg × 5"

    async def test_timed_picks_longest(self, imperial_coordinator) -> None:
        sets = [
            {"duration_seconds": 60},
            {"duration_seconds": 90},
        ]
        assert imperial_coordinator._get_best_set_string(sets) == "1m 30s"

    async def test_distance_with_duration(self, imperial_coordinator) -> None:
        sets = [{"distance_meters": 5000, "duration_seconds": 1500}]
        assert imperial_coordinator._get_best_set_string(sets) == "3.11 mi in 25m 00s"

    async def test_bodyweight_reps_only(self, imperial_coordinator) -> None:
        sets = [{"weight_kg": None, "reps": 20}]
        assert imperial_coordinator._get_best_set_string(sets) == "20 reps"


class TestCalculateTotalVolume:
    async def test_metric_volume(self, metric_coordinator) -> None:
        workout = {
            "exercises": [
                {
                    "sets": [
                        {"weight_kg": 60, "reps": 10},
                        {"weight_kg": 60, "reps": 8},
                    ]
                }
            ]
        }
        assert metric_coordinator._calculate_total_volume(workout) == 1080.0

    async def test_skips_sets_without_weight_or_reps(self, metric_coordinator) -> None:
        workout = {
            "exercises": [
                {
                    "sets": [
                        {"weight_kg": None, "reps": 20},
                        {"weight_kg": 50, "reps": None},
                        {"weight_kg": 50, "reps": 2},
                    ]
                }
            ]
        }
        assert metric_coordinator._calculate_total_volume(workout) == 100.0

    async def test_empty_workout(self, metric_coordinator) -> None:
        assert metric_coordinator._calculate_total_volume({}) == 0.0


class TestUpdateExercisePrs:
    async def test_tracks_heaviest_weight(self, imperial_coordinator) -> None:
        workouts = [
            {
                "exercises": [
                    {
                        "title": "Bench Press",
                        "exercise_template_id": "t1",
                        "sets": [{"weight_kg": 100, "reps": 5}],
                    }
                ]
            },
            {
                "exercises": [
                    {
                        "title": "Bench Press",
                        "exercise_template_id": "t1",
                        "sets": [{"weight_kg": 110, "reps": 1}],
                    }
                ]
            },
        ]
        imperial_coordinator._update_exercise_prs(workouts)
        assert imperial_coordinator._exercise_prs["bench press"]["weight_kg"] == 110

    async def test_equal_weight_more_reps_wins(self, imperial_coordinator) -> None:
        workouts = [
            {
                "exercises": [
                    {
                        "title": "Squat",
                        "sets": [
                            {"weight_kg": 100, "reps": 5},
                            {"weight_kg": 100, "reps": 8},
                        ],
                    }
                ]
            },
        ]
        imperial_coordinator._update_exercise_prs(workouts)
        assert imperial_coordinator._exercise_prs["squat"]["reps"] == 8

    async def test_tracks_distance_pr(self, imperial_coordinator) -> None:
        workouts = [
            {
                "exercises": [
                    {
                        "title": "Running",
                        "sets": [{"distance_meters": 3000}],
                    }
                ]
            },
            {
                "exercises": [
                    {
                        "title": "Running",
                        "sets": [{"distance_meters": 5000}],
                    }
                ]
            },
        ]
        imperial_coordinator._update_exercise_prs(workouts)
        assert (
            imperial_coordinator._exercise_distance_prs["running"]["distance_meters"]
            == 5000
        )


class TestCalculateCurrentStreak:
    async def test_no_workouts(self, imperial_coordinator) -> None:
        assert imperial_coordinator._calculate_current_streak([]) == 0

    async def test_workout_today(self, imperial_coordinator) -> None:
        workouts = [{"start_time": _iso(dt_util.utcnow())}]
        assert imperial_coordinator._calculate_current_streak(workouts) == 1

    async def test_today_and_yesterday(self, imperial_coordinator) -> None:
        now = dt_util.utcnow()
        workouts = [
            {"start_time": _iso(now)},
            {"start_time": _iso(now - timedelta(days=1))},
        ]
        assert imperial_coordinator._calculate_current_streak(workouts) == 2

    async def test_broken_streak(self, imperial_coordinator) -> None:
        workouts = [{"start_time": _iso(dt_util.utcnow() - timedelta(days=3))}]
        assert imperial_coordinator._calculate_current_streak(workouts) == 0


class TestFetch30DayWorkouts:
    async def test_single_page(self, imperial_coordinator, mock_client) -> None:
        now = dt_util.utcnow()
        mock_client.get_workouts.return_value = {
            "workouts": [
                {"id": "w1", "start_time": _iso(now)},
                {"id": "w2", "start_time": _iso(now - timedelta(days=2))},
            ],
            "page_count": 1,
        }
        result = await imperial_coordinator._fetch_30_day_workouts()
        assert [w["id"] for w in result] == ["w1", "w2"]
        assert mock_client.get_workouts.call_count == 1

    async def test_stops_at_cutoff(self, imperial_coordinator, mock_client) -> None:
        now = dt_util.utcnow()
        mock_client.get_workouts.return_value = {
            "workouts": [
                {"id": "recent", "start_time": _iso(now - timedelta(days=5))},
                {"id": "ancient", "start_time": _iso(now - timedelta(days=45))},
            ],
            "page_count": 3,
        }
        result = await imperial_coordinator._fetch_30_day_workouts()
        assert [w["id"] for w in result] == ["recent"]
        assert mock_client.get_workouts.call_count == 1

    async def test_paginates(self, imperial_coordinator, mock_client) -> None:
        now = dt_util.utcnow()
        mock_client.get_workouts.side_effect = [
            {
                "workouts": [{"id": "w1", "start_time": _iso(now - timedelta(days=1))}],
                "page_count": 2,
            },
            {
                "workouts": [{"id": "w2", "start_time": _iso(now - timedelta(days=2))}],
                "page_count": 2,
            },
        ]
        result = await imperial_coordinator._fetch_30_day_workouts()
        assert [w["id"] for w in result] == ["w1", "w2"]
        assert mock_client.get_workouts.call_count == 2

    async def test_stops_on_empty_page(self, imperial_coordinator, mock_client) -> None:
        mock_client.get_workouts.return_value = {"workouts": [], "page_count": 5}
        result = await imperial_coordinator._fetch_30_day_workouts()
        assert result == []
        assert mock_client.get_workouts.call_count == 1


class TestFetchRoutines:
    async def test_caches_full_set_detail(self, imperial_coordinator) -> None:
        await imperial_coordinator.fetch_routines()
        push_day = imperial_coordinator.routines[0]
        assert push_day["id"] == "r1"
        assert push_day["title"] == "Push Day"
        assert push_day["exercises"][0] == {
            "name": "Bench Press",
            "notes": "",
            "exercise_template_id": "t1",
            "sets": [
                {
                    "type": "warmup",
                    "weight_kg": 61.24,
                    "reps": 8,
                    "duration_seconds": None,
                    "distance_meters": None,
                },
                {
                    "type": "normal",
                    "weight_kg": 102.06,
                    "reps": 5,
                    "duration_seconds": None,
                    "distance_meters": None,
                },
            ],
        }
        assert push_day["exercises"][1]["sets"][0]["distance_meters"] == 4989

    async def test_exercise_without_sets(self, imperial_coordinator) -> None:
        await imperial_coordinator.fetch_routines()
        mobility = imperial_coordinator.routines[1]
        assert mobility["exercises"] == [
            {
                "name": "Hip Openers",
                "notes": "",
                "exercise_template_id": "t5",
                "sets": [],
            }
        ]

    async def test_routine_without_exercises(
        self, imperial_coordinator, mock_client
    ) -> None:
        mock_client.get_routines.return_value = {
            "routines": [{"id": "r9", "title": "Empty", "exercises": None}]
        }
        await imperial_coordinator.fetch_routines()
        assert imperial_coordinator.routines == [
            {"id": "r9", "title": "Empty", "exercises": []}
        ]


class TestDetectNextWorkout:
    async def test_no_routines(self, imperial_coordinator) -> None:
        result = imperial_coordinator._detect_next_workout()
        assert result["exercises_preview"] == []
        assert result["rotation_total"] == 0

    async def test_preview_is_exercise_titles(self, imperial_coordinator) -> None:
        await imperial_coordinator.fetch_routines()
        result = imperial_coordinator._detect_next_workout()
        assert result["next_routine"] == "Push Day"
        assert result["exercises_preview"] == ["Bench Press", "Running"]

    async def test_preview_after_last_workout(self, imperial_coordinator) -> None:
        await imperial_coordinator.fetch_routines()
        imperial_coordinator._workout_history = [
            {"routine_id": "r1", "title": "Push Day"}
        ]
        result = imperial_coordinator._detect_next_workout()
        assert result["routine_id"] == "r2"
        assert result["exercises_preview"] == ["Hip Openers"]


def _weights(count: int, first: int = 0, weight: float = 80.0) -> list[dict]:
    return [
        {"date": body_day(first + offset), "weight_kg": weight}
        for offset in range(count)
    ]


class TestBodyMeasurements:
    async def test_first_update_reads_every_page(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(50), {"date": body_day(50), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        await metric_coordinator._update_body_measurements()
        assert mock_client.get_body_measurements.call_count == 8
        assert metric_coordinator._body_measurements[body_day(50)]["waist"] == 81

    async def test_fetch_treats_404_as_empty(
        self, metric_coordinator, mock_client
    ) -> None:
        mock_client.get_body_measurements.side_effect = HevyNotFoundError("404")
        await metric_coordinator._update_body_measurements()
        assert metric_coordinator._body_measurements == {}

    async def test_regular_update_reads_newest_pages_and_keeps_older_entries(
        self, metric_coordinator, mock_client
    ) -> None:
        older = [{"date": body_day(60), "waist": 81}, *_weights(5, first=61)]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements([*_weights(55), *older])
        )
        await metric_coordinator._update_body_measurements()

        newest = [*_weights(1, weight=79.0), *_weights(53, first=2)]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements([*newest, *older])
        )
        await metric_coordinator._update_body_measurements()

        stored = metric_coordinator._body_measurements
        assert mock_client.get_body_measurements.call_count == 5
        assert stored[body_day(0)]["weight_kg"] == 79.0
        assert body_day(1) not in stored
        assert stored[body_day(60)]["waist"] == 81

    async def test_daily_full_sync_drops_deleted_older_entries(
        self, metric_coordinator, mock_client, freezer
    ) -> None:
        older = [{"date": body_day(60), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements([*_weights(55), *older])
        )
        await metric_coordinator._update_body_measurements()
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(_weights(55))
        )

        await metric_coordinator._update_body_measurements()
        assert body_day(60) in metric_coordinator._body_measurements

        freezer.tick(timedelta(hours=24))
        await metric_coordinator._update_body_measurements()
        assert body_day(60) not in metric_coordinator._body_measurements
        assert mock_client.get_body_measurements.call_count == 13

    async def test_summary_keeps_last_logged_value_per_field(
        self, metric_coordinator
    ) -> None:
        summary = metric_coordinator._summarize_body_measurements(
            [
                {"date": "2026-03-09", "weight_kg": 78.5, "waist": None},
                {"date": "2026-03-02", "weight_kg": 80.0, "waist": 81},
            ]
        )
        assert summary["latest_date"] == "2026-03-09"
        assert summary["values"]["weight_kg"]["change"] == -1.5
        assert summary["values"]["waist"] == {
            "value": 81,
            "date": "2026-03-02",
            "previous_value": None,
            "previous_date": None,
            "change": None,
        }
        assert "neck_cm" not in summary["values"]

    async def test_summary_empty(self, metric_coordinator) -> None:
        assert metric_coordinator._summarize_body_measurements([]) == {
            "latest_date": None,
            "values": {},
            "history": [],
        }

    async def test_failure_keeps_workout_update_and_last_values(
        self, metric_coordinator, mock_client
    ) -> None:
        mock_client.get_body_measurements.return_value = {
            "body_measurements": [{"date": "2026-03-02", "weight_kg": 80.0}],
            "page_count": 1,
        }
        await metric_coordinator._async_update_data()
        mock_client.get_body_measurements.side_effect = HevyApiError("HTTP 500")
        data = await metric_coordinator._async_update_data()
        assert data["body_measurements"]["values"]["weight_kg"]["value"] == 80.0

    async def test_regular_update_drops_deleted_newest_entry(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(1, weight=79.0), *_weights(59, first=1)]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        await metric_coordinator._update_body_measurements()

        del entries[0]
        mock_client.get_body_measurements.reset_mock()
        await metric_coordinator._update_body_measurements()

        stored = metric_coordinator._body_measurements
        assert mock_client.get_body_measurements.call_count == 5
        assert body_day(0) not in stored
        assert body_day(59) in stored
        summary = metric_coordinator._summarize_body_measurements(stored.values())
        assert summary["latest_date"] == body_day(1)
        assert summary["values"]["weight_kg"]["value"] == 80.0

    @pytest.mark.parametrize(
        "response",
        [
            json.JSONDecodeError("Expecting value", "<html>", 0),
            ValueError("Invalid JSON"),
            [],
            {"body_measurements": "invalid", "page_count": 1},
            {"body_measurements": ["invalid"], "page_count": 1},
            {"body_measurements": [{"date": 20260302}], "page_count": 1},
            {"body_measurements": [{"date": None}], "page_count": 1},
            {"body_measurements": [{"weight_kg": 80.0}], "page_count": 1},
            {"body_measurements": [], "page_count": "1"},
            {},
            {"page_count": 1},
            {"body_measurements": False, "page_count": 1},
            {"body_measurements": {}, "page_count": 1},
            {"body_measurements": "", "page_count": 1},
            {"body_measurements": None, "page_count": 1},
            {"body_measurements": 0, "page_count": 1},
            {"body_measurements": [], "page_count": False},
            {"body_measurements": [], "page_count": None},
            {"body_measurements": [], "page_count": -1},
        ],
    )
    async def test_invalid_response_keeps_workout_update_and_last_values(
        self, metric_coordinator, mock_client, response
    ) -> None:
        mock_client.get_workout_count.return_value = 42
        mock_client.get_body_measurements.return_value = {
            "body_measurements": [{"date": "2026-03-02", "weight_kg": 80.0}],
            "page_count": 1,
        }
        await metric_coordinator._async_update_data()

        if isinstance(response, Exception):
            mock_client.get_body_measurements.side_effect = response
        else:
            mock_client.get_body_measurements.return_value = response
        data = await metric_coordinator._async_update_data()

        assert data["workout_count"] == 42
        assert data["body_measurements"]["values"]["weight_kg"]["value"] == 80.0

    async def test_invalid_page_during_full_read_stores_nothing_from_it(
        self, metric_coordinator, mock_client
    ) -> None:
        pages = paged_body_measurements(_weights(30))

        async def get_body_measurements(page: int = 1, page_size: int = 10) -> dict:
            if page == 2:
                raise json.JSONDecodeError("Expecting value", "<html>", 0)
            return await pages(page, page_size)

        mock_client.get_body_measurements = AsyncMock(side_effect=get_body_measurements)
        with pytest.raises(HevyApiError):
            await metric_coordinator._update_body_measurements()
        assert metric_coordinator._body_measurements == {}

        mock_client.get_body_measurements = AsyncMock(side_effect=pages)
        await metric_coordinator._update_body_measurements()
        assert len(metric_coordinator._body_measurements) == 30

    async def test_full_read_continues_in_batches_until_oldest_entry(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(2000), {"date": body_day(2000), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )

        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            mock_client.get_body_measurements.reset_mock()
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert mock_client.get_body_measurements.call_count <= (
                MAX_BODY_MEASUREMENT_PAGES + BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE
            )
            assert updates < 20

        assert updates > 1
        assert metric_coordinator._body_measurements[body_day(2000)]["waist"] == 81
        assert len(metric_coordinator._body_measurements) == len(entries)

        mock_client.get_body_measurements.reset_mock()
        await metric_coordinator._update_body_measurements()
        assert (
            mock_client.get_body_measurements.call_count == MAX_BODY_MEASUREMENT_PAGES
        )
        assert len(metric_coordinator._body_measurements) == len(entries)

    async def test_batched_full_read_drops_entries_deleted_since_last_read(
        self, metric_coordinator, mock_client, freezer
    ) -> None:
        entries = [*_weights(300), {"date": body_day(300), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()

        del entries[250]
        freezer.tick(timedelta(hours=24))
        await metric_coordinator._update_body_measurements()
        assert body_day(250) in metric_coordinator._body_measurements
        while metric_coordinator._body_measurement_sync_page is not None:
            await metric_coordinator._update_body_measurements()

        stored = metric_coordinator._body_measurements
        assert body_day(250) not in stored
        assert stored[body_day(300)]["waist"] == 81
        assert set(stored) == {entry["date"] for entry in entries}

    async def test_batched_full_read_restarts_when_pages_move(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(300), {"date": body_day(300), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        await metric_coordinator._update_body_measurements()
        read_first = set(metric_coordinator._body_measurements)

        # Removing more than a page of newer entries moves older ones onto
        # pages the next batch would not read
        del entries[:15]
        await metric_coordinator._update_body_measurements()
        assert metric_coordinator._body_measurement_sync_page == 1
        remaining = {entry["date"] for entry in entries}
        assert read_first & remaining <= set(metric_coordinator._body_measurements)

        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
        assert set(metric_coordinator._body_measurements) == remaining

    async def test_valid_empty_response_clears_deleted_entries(
        self, metric_coordinator, mock_client, freezer
    ) -> None:
        mock_client.get_body_measurements.return_value = {
            "body_measurements": [{"date": "2026-03-02", "weight_kg": 80.0}],
            "page_count": 1,
        }
        await metric_coordinator._async_update_data()

        mock_client.get_body_measurements.return_value = {
            "body_measurements": [],
            "page_count": 0,
        }
        data = await metric_coordinator._async_update_data()

        assert metric_coordinator._body_measurements == {}
        assert data["body_measurements"]["values"] == {}

    async def test_batched_full_read_drops_entry_deleted_on_reread_page(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(300), {"date": body_day(300), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        await metric_coordinator._update_body_measurements()
        deleted = len(metric_coordinator._body_measurements) - 5
        assert body_day(deleted) in metric_coordinator._body_measurements

        del entries[deleted]
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
        await metric_coordinator._update_body_measurements()

        stored = metric_coordinator._body_measurements
        assert body_day(deleted) not in stored
        assert set(stored) == {entry["date"] for entry in entries}

    async def test_batched_full_read_recovers_entry_moved_onto_read_page(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = _weights(301)
        entries[100] = {"date": body_day(100), "waist": 77}
        pages = paged_body_measurements(entries)
        deleted = False

        async def get_body_measurements(page: int = 1, page_size: int = 10) -> dict:
            nonlocal deleted
            if page == 11 and not deleted:
                deleted = True
                del entries[0]
            return await pages(page, page_size)

        mock_client.get_body_measurements = AsyncMock(side_effect=get_body_measurements)
        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            mock_client.get_body_measurements.reset_mock()
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert mock_client.get_body_measurements.call_count <= (
                MAX_BODY_MEASUREMENT_PAGES + BODY_MEASUREMENT_SYNC_PAGES_PER_UPDATE
            )
            assert updates < 10
        await metric_coordinator._update_body_measurements()

        assert deleted
        stored = metric_coordinator._body_measurements
        assert stored[body_day(100)]["waist"] == 77
        assert set(stored) == {entry["date"] for entry in entries}
        summary = metric_coordinator._summarize_body_measurements(stored.values())
        assert summary["values"]["waist"]["value"] == 77

    async def test_batched_full_read_keeps_entries_when_newer_entry_is_added(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = _weights(301, first=1)
        pages = paged_body_measurements(entries)
        added = False

        async def get_body_measurements(page: int = 1, page_size: int = 10) -> dict:
            nonlocal added
            if page == 11 and not added:
                added = True
                entries.insert(0, {"date": body_day(0), "weight_kg": 79.0})
            return await pages(page, page_size)

        mock_client.get_body_measurements = AsyncMock(side_effect=get_body_measurements)
        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert updates < 10

        assert added
        stored = metric_coordinator._body_measurements
        assert set(stored) == {entry["date"] for entry in entries}
        assert stored[body_day(0)]["weight_kg"] == 79.0

    async def test_batched_full_read_recovers_entry_moved_before_page_check(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(301), {"date": body_day(301), "waist": 81}]
        pages = paged_body_measurements(entries)
        mock_client.get_body_measurements = AsyncMock(side_effect=pages)
        await metric_coordinator._update_body_measurements()
        last_page = -(-len(entries) // 10)
        deleted = False

        async def get_body_measurements(page: int = 1, page_size: int = 10) -> dict:
            nonlocal deleted
            if page == last_page and not deleted:
                deleted = True
                del entries[0]
            return await pages(page, page_size)

        mock_client.get_body_measurements = AsyncMock(side_effect=get_body_measurements)
        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert updates < 10
        await metric_coordinator._update_body_measurements()

        assert deleted
        assert set(metric_coordinator._body_measurements) == {
            entry["date"] for entry in entries
        }

    async def test_batched_full_read_drops_newest_entry_deleted_on_reread_page(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = [*_weights(300), {"date": body_day(300), "waist": 81}]
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        await metric_coordinator._update_body_measurements()
        deleted = (metric_coordinator._body_measurement_sync_page - 1) * 10
        assert body_day(deleted) in metric_coordinator._body_measurements

        del entries[deleted]
        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert updates < 10
        await metric_coordinator._update_body_measurements()

        stored = metric_coordinator._body_measurements
        assert body_day(deleted) not in stored
        assert set(stored) == {entry["date"] for entry in entries}

    async def test_step_back_never_reads_before_first_page(
        self, metric_coordinator, mock_client
    ) -> None:
        entries = _weights(301)
        mock_client.get_body_measurements = AsyncMock(
            side_effect=paged_body_measurements(entries)
        )
        metric_coordinator._body_measurement_sync_page = 1
        metric_coordinator._body_measurement_sync_oldest = body_day(25)
        metric_coordinator._body_measurement_sync_anchor = body_day(-1)

        updates = 0
        while metric_coordinator._body_measurements_synced is None:
            await metric_coordinator._update_body_measurements()
            updates += 1
            assert updates < 20

        pages = [
            call.kwargs["page"] for call in mock_client.get_body_measurements.mock_calls
        ]
        assert min(pages) == 1
        assert set(metric_coordinator._body_measurements) == {
            entry["date"] for entry in entries
        }
