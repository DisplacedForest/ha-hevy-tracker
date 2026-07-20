from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hevy.const import UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC
from custom_components.hevy.coordinator import HevyDataUpdateCoordinator


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
    client.get_routines = AsyncMock(return_value={"routines": []})
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
