from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.hevy.api import HevyApiClient, HevyApiError


async def test_http_errors_do_not_expose_upstream_body(caplog):
    response = MagicMock(status=500)
    response.text = AsyncMock(return_value="sensitive-upstream-value")
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    session = MagicMock()
    session.request.return_value = request
    client = HevyApiClient("synthetic-key", session)
    with pytest.raises(HevyApiError, match="HTTP 500") as caught:
        await client.validate_api_key()
    assert "sensitive-upstream-value" not in str(caught.value)
    assert "sensitive-upstream-value" not in caplog.text
    assert "synthetic-key" not in caplog.text
    response.text.assert_not_called()


async def test_connection_error_does_not_expose_transport_details():
    session = MagicMock()
    session.request.side_effect = aiohttp.ClientError("sensitive-transport-value")
    client = HevyApiClient("synthetic-key", session)
    with pytest.raises(HevyApiError, match="Connection to Hevy failed") as caught:
        await client.get_workout_count()
    assert "sensitive-transport-value" not in str(caught.value)


async def test_user_info_uses_authenticated_account_endpoint():
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"data": {"id": "user-one", "name": "Sam"}})
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    session = MagicMock()
    session.request.return_value = request
    client = HevyApiClient("fixture-key", session)
    assert await client.get_user_info() == {"data": {"id": "user-one", "name": "Sam"}}
    args, kwargs = session.request.call_args
    assert args[0] == "GET"
    assert args[1].endswith("/v1/user/info")
    assert kwargs["headers"] == {"api-key": "fixture-key"}
