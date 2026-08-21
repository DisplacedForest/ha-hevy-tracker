from __future__ import annotations

from datetime import timedelta

from homeassistant.util import dt as dt_util


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
        assert (
            imperial_coordinator._get_best_set_string(sets) == "3.11 mi in 25m 00s"
        )

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
                "workouts": [
                    {"id": "w1", "start_time": _iso(now - timedelta(days=1))}
                ],
                "page_count": 2,
            },
            {
                "workouts": [
                    {"id": "w2", "start_time": _iso(now - timedelta(days=2))}
                ],
                "page_count": 2,
            },
        ]
        result = await imperial_coordinator._fetch_30_day_workouts()
        assert [w["id"] for w in result] == ["w1", "w2"]
        assert mock_client.get_workouts.call_count == 2

    async def test_stops_on_empty_page(
        self, imperial_coordinator, mock_client
    ) -> None:
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
