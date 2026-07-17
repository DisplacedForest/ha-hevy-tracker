"""Calendar platform for Hevy Workout Tracker."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import logging
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_API_KEY, DOMAIN
from .coordinator import HevyDataUpdateCoordinator
from .sensor import get_device_info

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _parse_dt(date_str: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string from the Hevy API.

    Args:
        date_str: ISO datetime string (e.g., "2026-01-15T10:30:00Z")

    Returns:
        Timezone-aware datetime, or None if parsing fails
    """
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _build_event_description(workout: dict[str, Any]) -> str | None:
    """Build a human-readable description from workout exercise data.

    Args:
        workout: Raw workout dict from the Hevy API

    Returns:
        Formatted description string, or None if no exercises
    """
    exercises = workout.get("exercises", [])
    if not exercises:
        return None

    lines: list[str] = []
    for exercise in exercises:
        title = exercise.get("title", "Unknown")
        sets = exercise.get("sets", [])
        set_count = len(sets)

        # Sum up volume for weighted exercises
        total_volume = 0.0
        has_weight = False
        for s in sets:
            weight_kg = s.get("weight_kg")
            reps = s.get("reps")
            if weight_kg is not None and reps is not None:
                total_volume += weight_kg * reps
                has_weight = True

        if has_weight and total_volume > 0:
            lines.append(
                f"{title}: {set_count} sets, {round(total_volume, 1)} kg volume"
            )
        else:
            lines.append(f"{title}: {set_count} sets")

    return "\n".join(lines)


def _workout_to_event(workout: dict[str, Any]) -> CalendarEvent | None:
    """Convert a raw Hevy workout dict to a CalendarEvent.

    Args:
        workout: Raw workout dict from the Hevy API

    Returns:
        CalendarEvent instance, or None if start_time is missing or invalid
    """
    start_dt = _parse_dt(workout.get("start_time"))
    if start_dt is None:
        return None

    end_dt = _parse_dt(workout.get("end_time"))
    if end_dt is None:
        end_dt = start_dt + timedelta(hours=1)

    title = workout.get("title") or "Workout"
    description = _build_event_description(workout)

    return CalendarEvent(
        start=start_dt,
        end=end_dt,
        summary=title,
        description=description,
        uid=workout.get("id"),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hevy calendar entity.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: HevyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HevyCalendarEntity(coordinator, entry)])


class HevyCalendarEntity(CoordinatorEntity[HevyDataUpdateCoordinator], CalendarEntity):
    """Calendar entity that displays Hevy workouts as calendar events."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        coordinator: HevyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar entity.

        Args:
            coordinator: Data coordinator with cached workout data
            entry: Config entry for device info and unique ID
        """
        super().__init__(coordinator)
        self._entry = entry

        api_key = entry.data[CONF_API_KEY]
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        self._attr_unique_id = f"{key_hash}_workout_calendar"
        self._attr_name = "Workout calendar"
        self._attr_device_info = get_device_info(entry)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the most recent workout as the current event.

        The coordinator caches 30 days of workout history (all past events).
        There are no upcoming events since Hevy does not schedule future workouts.
        This returns the latest workout so the calendar card always shows something.
        """
        if not self.coordinator.data:
            return None

        workouts: list[dict[str, Any]] = self.coordinator.data.get("workouts", [])
        if not workouts:
            return None

        # Workouts are sorted most-recent-first
        return _workout_to_event(workouts[0])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return workout events within the given date range.

        Called by HA when the calendar view queries for events, or when
        external CalDAV clients request a sync.

        Args:
            hass: Home Assistant instance
            start_date: Start of the query range (inclusive)
            end_date: End of the query range (exclusive)

        Returns:
            List of CalendarEvents sorted by start time
        """
        if not self.coordinator.data:
            return []

        workouts: list[dict[str, Any]] = self.coordinator.data.get("workouts", [])

        events: list[CalendarEvent] = []
        for workout in workouts:
            start_dt = _parse_dt(workout.get("start_time"))
            if start_dt is None:
                continue
            # Filter to the requested range
            if start_dt < start_date or start_dt >= end_date:
                continue
            event = _workout_to_event(workout)
            if event is not None:
                events.append(event)

        events.sort(key=lambda e: e.start)
        return events
