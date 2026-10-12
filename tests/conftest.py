from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hevy.api import HevyNotFoundError
from custom_components.hevy.const import UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC
from custom_components.hevy.coordinator import HevyDataUpdateCoordinator

ROUTINES_RESPONSE = {
    "routines": [
        {
            "id": "r1",
            "title": "Push Day",
            "exercises": [
                {
                    "title": "Bench Press",
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
                },
                {
                    "title": "Running",
                    "exercise_template_id": "t3",
                    "sets": [
                        {
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "duration_seconds": 1500,
                            "distance_meters": 4989,
                        }
                    ],
                },
            ],
        },
        {
            "id": "r2",
            "title": "Mobility",
            "exercises": [
                {
                    "title": "Hip Openers",
                    "exercise_template_id": "t5",
                    "sets": None,
                }
            ],
        },
    ]
}


def body_day(days_ago: int) -> str:
    return (date(2026, 3, 31) - timedelta(days=days_ago)).isoformat()


def paged_body_measurements(
    entries: list[dict[str, Any]],
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    async def get_body_measurements(page: int = 1, page_size: int = 10) -> dict:
        chunk = entries[(page - 1) * page_size : page * page_size]
        if not chunk:
            raise HevyNotFoundError("Hevy returned HTTP 404")
        return {
            "page": page,
            "page_count": -(-len(entries) // page_size),
            "body_measurements": chunk,
        }

    return get_body_measurements


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_user_info = AsyncMock(return_value={"data": {"name": "Test account"}})
    client.get_workout_count = AsyncMock(return_value=0)
    client.get_workouts = AsyncMock(return_value={"workouts": [], "page_count": 1})
    client.get_workout_events = AsyncMock(return_value={"events": []})
    client.get_exercise_templates = AsyncMock(
        return_value={"exercise_templates": [], "page_count": 1}
    )
    client.get_routines = AsyncMock(return_value=ROUTINES_RESPONSE)
    client.get_body_measurements = AsyncMock(
        return_value={"body_measurements": [], "page_count": 1}
    )
    return client


@pytest.fixture
async def imperial_coordinator(hass, mock_client) -> HevyDataUpdateCoordinator:
    return HevyDataUpdateCoordinator(
        hass, mock_client, timedelta(minutes=15), UNIT_SYSTEM_IMPERIAL
    )


@pytest.fixture
async def metric_coordinator(hass, mock_client) -> HevyDataUpdateCoordinator:
    return HevyDataUpdateCoordinator(
        hass, mock_client, timedelta(minutes=15), UNIT_SYSTEM_METRIC
    )
