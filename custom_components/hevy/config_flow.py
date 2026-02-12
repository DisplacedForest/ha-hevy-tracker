"""Config flow for Hevy Workout Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import HevyApiClient, HevyApiError, HevyAuthError
from .const import (
    CONF_API_KEY,
    CONF_POLLING_INTERVAL,
    CONF_UNIT_SYSTEM,
    DEFAULT_NAME,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_UNIT_SYSTEM,
    DOMAIN,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_SYSTEM_METRIC,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_key(hass: HomeAssistant, api_key: str) -> dict[str, str]:
    """Validate the API key by attempting to authenticate.

    Args:
        hass: Home Assistant instance
        api_key: The Hevy API key to validate

    Returns:
        Dict with validation info

    Raises:
        HevyAuthError: If authentication fails
        HevyApiError: If API request fails
    """
    session = async_get_clientsession(hass)
    client = HevyApiClient(api_key, session)

    try:
        await client.validate_api_key()
        workout_count = await client.get_workout_count()
        return {"title": DEFAULT_NAME, "workout_count": workout_count}
    finally:
        # Don't close session as it's managed by HA
        pass


class HevyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hevy Workout Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.

        Args:
            user_input: User input data

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]

            try:
                info = await validate_api_key(self.hass, api_key)
            except HevyAuthError:
                errors["base"] = "invalid_auth"
            except HevyApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during API validation")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(api_key)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_API_KEY: api_key},
                    options={
                        CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                        CONF_UNIT_SYSTEM: DEFAULT_UNIT_SYSTEM,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HevyOptionsFlowHandler:
        """Get the options flow for this handler.

        Args:
            config_entry: Config entry instance

        Returns:
            Options flow handler
        """
        return HevyOptionsFlowHandler()


class HevyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Hevy options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options.

        Args:
            user_input: User input data

        Returns:
            Flow result
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLLING_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
                    vol.Optional(
                        CONF_UNIT_SYSTEM,
                        default=self.config_entry.options.get(
                            CONF_UNIT_SYSTEM, DEFAULT_UNIT_SYSTEM
                        ),
                    ): vol.In([UNIT_SYSTEM_IMPERIAL, UNIT_SYSTEM_METRIC]),
                }
            ),
        )
