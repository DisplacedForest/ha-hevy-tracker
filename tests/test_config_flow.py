from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hevy.const import (
    CONF_API_KEY,
    CONF_POLLING_INTERVAL,
    CONF_UNIT_SYSTEM,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_UNIT_SYSTEM,
    DOMAIN,
    UNIT_SYSTEM_METRIC,
)


async def test_user_form_validates_and_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"]
    with pytest.raises(vol.Invalid):
        schema({})
    user_input = schema({CONF_API_KEY: "test-key"})
    with (
        patch(
            "custom_components.hevy.config_flow.validate_api_key",
            AsyncMock(return_value={"title": "Hevy", "workout_count": 0}),
        ),
        patch("custom_components.hevy.async_setup_entry", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_API_KEY: "test-key"}
    assert result["options"] == {
        CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
        CONF_UNIT_SYSTEM: DEFAULT_UNIT_SYSTEM,
    }


@pytest.mark.parametrize("existing_options", [{}, {CONF_POLLING_INTERVAL: 25}])
async def test_options_form_defaults_validation_and_save(hass, existing_options):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options=existing_options,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"]
    assert schema({}) == {
        CONF_POLLING_INTERVAL: existing_options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        ),
        CONF_UNIT_SYSTEM: DEFAULT_UNIT_SYSTEM,
    }
    for invalid in (
        {CONF_POLLING_INTERVAL: 4},
        {CONF_POLLING_INTERVAL: 121},
        {CONF_UNIT_SYSTEM: "invalid"},
    ):
        with pytest.raises(vol.Invalid):
            schema(invalid)
    options = schema(
        {CONF_POLLING_INTERVAL: "30", CONF_UNIT_SYSTEM: UNIT_SYSTEM_METRIC}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == options
