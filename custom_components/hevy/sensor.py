"""Sensor platform for Hevy Workout Tracker."""
from __future__ import annotations

from datetime import datetime
import hashlib
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_API_KEY,
    DOMAIN,
    SENSOR_CURRENT_STREAK,
    SENSOR_LAST_WORKOUT_DATE,
    SENSOR_LAST_WORKOUT_SUMMARY,
    SENSOR_WEEKLY_WORKOUT_COUNT,
    SENSOR_WORKOUT_COUNT,
)
from .coordinator import HevyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hevy sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: HevyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create static sensors
    entities: list[SensorEntity | BinarySensorEntity] = [
        HevyWorkoutCountSensor(coordinator, entry),
        HevyLastWorkoutDateSensor(coordinator, entry),
        HevyLastWorkoutSummarySensor(coordinator, entry),
        HevyWeeklyWorkoutCountSensor(coordinator, entry),
        HevyCurrentStreakSensor(coordinator, entry),
        HevyWorkedOutTodayBinarySensor(coordinator, entry),
        HevyWorkedOutThisWeekBinarySensor(coordinator, entry),
    ]

    # Create per-exercise sensors dynamically
    if coordinator.data:
        exercise_data = coordinator.data.get("exercise_data", {})
        for exercise_key, exercise_info in exercise_data.items():
            entities.append(HevyExerciseSensor(coordinator, entry, exercise_key))

    async_add_entities(entities)

    # Register update listener to add new exercise sensors
    async def async_add_new_exercise_sensors() -> None:
        """Add sensors for newly discovered exercises."""
        if not coordinator.data:
            return

        exercise_data = coordinator.data.get("exercise_data", {})
        existing_exercises = {
            entity.exercise_key
            for entity in hass.data[DOMAIN].get(f"{entry.entry_id}_exercises", set())
            if isinstance(entity, HevyExerciseSensor)
        }

        new_entities = []
        for exercise_key in exercise_data:
            if exercise_key not in existing_exercises:
                new_entities.append(HevyExerciseSensor(coordinator, entry, exercise_key))
                existing_exercises.add(exercise_key)

        if new_entities:
            async_add_entities(new_entities)

        # Store tracked exercises
        if f"{entry.entry_id}_exercises" not in hass.data[DOMAIN]:
            hass.data[DOMAIN][f"{entry.entry_id}_exercises"] = set()
        hass.data[DOMAIN][f"{entry.entry_id}_exercises"].update(existing_exercises)

    coordinator.async_add_listener(async_add_new_exercise_sensors)


def get_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Get device info for grouping entities.

    Args:
        entry: Config entry

    Returns:
        Device info dict
    """
    api_key = entry.data[CONF_API_KEY]
    device_id = hashlib.md5(api_key.encode()).hexdigest()[:8]

    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name="Hevy Workout Tracker",
        manufacturer="Hevy",
        model="Workout Tracker",
        entry_type="service",
    )


class HevyBaseSensor(CoordinatorEntity[HevyDataUpdateCoordinator], SensorEntity):
    """Base class for Hevy sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HevyDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data coordinator
            entry: Config entry
            sensor_type: Type of sensor
        """
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type

        api_key = entry.data[CONF_API_KEY]
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        self._attr_unique_id = f"{key_hash}_{sensor_type}"
        self._attr_device_info = get_device_info(entry)


class HevyWorkoutCountSensor(HevyBaseSensor):
    """Sensor for total workout count."""

    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_WORKOUT_COUNT)
        self._attr_name = "Workout count"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("workout_count")


class HevyLastWorkoutDateSensor(HevyBaseSensor):
    """Sensor for last workout date."""

    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = "timestamp"

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_LAST_WORKOUT_DATE)
        self._attr_name = "Last workout date"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        date_str = self.coordinator.data.get("last_workout_date")
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "workout_title": self.coordinator.data.get("last_workout_title"),
            "duration_minutes": self.coordinator.data.get("workout_duration_minutes"),
        }


class HevyLastWorkoutSummarySensor(HevyBaseSensor):
    """Sensor for last workout summary."""

    _attr_icon = "mdi:notebook"

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_LAST_WORKOUT_SUMMARY)
        self._attr_name = "Last workout summary"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("last_workout_title") or "No workouts"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        last_workout = self.coordinator.data.get("last_workout")
        if not last_workout:
            return {}

        return {
            "date": self.coordinator.data.get("last_workout_date"),
            "duration_minutes": self.coordinator.data.get("workout_duration_minutes"),
            "total_volume": self.coordinator.data.get("total_volume"),
            "total_volume_unit": self.coordinator.data.get("total_volume_unit"),
            "exercise_count": len(self.coordinator.data.get("exercises_summary", [])),
            "exercises": self.coordinator.data.get("exercises_summary", []),
        }


class HevyWeeklyWorkoutCountSensor(HevyBaseSensor):
    """Sensor for weekly workout count."""

    _attr_icon = "mdi:calendar-week"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_WEEKLY_WORKOUT_COUNT)
        self._attr_name = "Weekly workout count"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("weekly_workout_count", 0)


class HevyCurrentStreakSensor(HevyBaseSensor):
    """Sensor for current workout streak."""

    _attr_icon = "mdi:fire"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "days"

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_CURRENT_STREAK)
        self._attr_name = "Current streak"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("current_streak", 0)


class HevyWorkedOutTodayBinarySensor(
    CoordinatorEntity[HevyDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for worked out today."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

        api_key = entry.data[CONF_API_KEY]
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        self._attr_unique_id = f"{key_hash}_worked_out_today"
        self._attr_name = "Worked out today"
        self._attr_device_info = get_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return true if worked out today."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("worked_out_today", False)


class HevyWorkedOutThisWeekBinarySensor(
    CoordinatorEntity[HevyDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for worked out this week."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self, coordinator: HevyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

        api_key = entry.data[CONF_API_KEY]
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        self._attr_unique_id = f"{key_hash}_worked_out_this_week"
        self._attr_name = "Worked out this week"
        self._attr_device_info = get_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return true if worked out this week."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("worked_out_this_week", False)


class HevyExerciseSensor(CoordinatorEntity[HevyDataUpdateCoordinator], SensorEntity):
    """Sensor for individual exercise tracking."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HevyDataUpdateCoordinator,
        entry: ConfigEntry,
        exercise_key: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data coordinator
            entry: Config entry
            exercise_key: Exercise identifier (lowercase title)
        """
        super().__init__(coordinator)
        self._entry = entry
        self.exercise_key = exercise_key

        api_key = entry.data[CONF_API_KEY]
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        exercise_id = exercise_key.replace(" ", "_").replace("(", "").replace(")", "")
        self._attr_unique_id = f"{key_hash}_exercise_{exercise_id}"
        self._attr_device_info = get_device_info(entry)

        # Set icon based on exercise type
        self._attr_icon = "mdi:weight-lifter"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        exercise_data = self._get_exercise_data()
        if exercise_data:
            display_name = exercise_data.get("display_name", self.exercise_key)
            return f"{display_name}"
        return self.exercise_key.title()

    def _get_exercise_data(self) -> dict[str, Any] | None:
        """Get exercise data from coordinator."""
        if not self.coordinator.data:
            return None
        exercise_data = self.coordinator.data.get("exercise_data", {})
        return exercise_data.get(self.exercise_key)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor (best set)."""
        exercise_data = self._get_exercise_data()
        if not exercise_data:
            return None
        return exercise_data.get("best_set", "No data")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._get_exercise_data() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        exercise_data = self._get_exercise_data()
        if not exercise_data:
            return {}

        attrs = {
            "last_workout_date": exercise_data.get("last_workout_date"),
            "last_workout_sets": exercise_data.get("last_workout_sets", []),
            "total_sets": exercise_data.get("total_sets", 0),
            "exercise_template_id": exercise_data.get("exercise_template_id"),
            "notes": exercise_data.get("notes"),
        }

        # Enrich with template data if available
        template_id = exercise_data.get("exercise_template_id")
        if template_id and template_id in self.coordinator._exercise_templates:
            template = self.coordinator._exercise_templates[template_id]
            attrs.update(
                {
                    "muscle_group": template.get("muscle_group"),
                    "secondary_muscles": template.get("secondary_muscle_groups"),
                    "equipment": template.get("equipment"),
                    "exercise_type": template.get("type"),
                }
            )

        # Add weight and reps for weighted exercises
        if exercise_data.get("weight") is not None:
            attrs["weight"] = exercise_data.get("weight")
            attrs["weight_unit"] = exercise_data.get("weight_unit")
            attrs["total_reps"] = exercise_data.get("total_reps")
            attrs["personal_record_weight"] = exercise_data.get("personal_record_weight")
            attrs["personal_record_reps"] = exercise_data.get("personal_record_reps")

        # Add duration for timed exercises
        if exercise_data.get("total_duration_seconds") is not None:
            attrs["total_duration_seconds"] = exercise_data.get("total_duration_seconds")

        return attrs
