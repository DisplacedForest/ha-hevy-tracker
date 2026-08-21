from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_workout_count = AsyncMock(return_value=0)
    client.get_workouts = AsyncMock(return_value={"workouts": [], "page_count": 1})
    client.get_workout_events = AsyncMock(return_value={"events": []})
    client.get_exercise_templates = AsyncMock(
        return_value={"exercise_templates": [], "page_count": 1}
    )
    client.get_routines = AsyncMock(return_value=ROUTINES_RESPONSE)
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
