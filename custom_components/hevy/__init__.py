"""The Hevy Workout Tracker integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HevyApiClient
from .const import (
    CONF_API_KEY,
    CONF_POLLING_INTERVAL,
    CONF_UNIT_SYSTEM,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_UNIT_SYSTEM,
    DOMAIN,
)
from .coordinator import HevyDataUpdateCoordinator
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hevy Workout Tracker from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup succeeded
    """
    hass.data.setdefault(DOMAIN, {})

    api_key = entry.data[CONF_API_KEY]
    session = async_get_clientsession(hass)
    client = HevyApiClient(api_key, session)

    # Get polling interval and unit system from options or use defaults
    polling_interval_minutes = entry.options.get(
        CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
    )
    unit_system = entry.options.get(CONF_UNIT_SYSTEM, DEFAULT_UNIT_SYSTEM)
    update_interval = timedelta(minutes=polling_interval_minutes)

    coordinator = HevyDataUpdateCoordinator(hass, client, update_interval, unit_system)

    # Fetch exercise templates and routines before first data refresh
    await coordinator.fetch_exercise_templates()
    await coordinator.fetch_routines()

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async_register_services(hass)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload succeeded
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unregister_services(hass)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    await hass.config_entries.async_reload(entry.entry_id)
