"""Hevy API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class HevyApiError(Exception):
    """Base exception for Hevy API errors."""


class HevyAuthError(HevyApiError):
    """Exception for authentication errors."""


class HevyApiClient:
    """Hevy API Client."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the API client.

        Args:
            api_key: The Hevy API key
            session: Optional aiohttp session (will create one if not provided)
        """
        self._api_key = api_key
        self._session = session
        self._own_session = session is None

    async def __aenter__(self) -> HevyApiClient:
        """Async enter."""
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async exit."""
        if self._own_session and self._session:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/workouts")
            params: Optional query parameters

        Returns:
            Response data as dict

        Raises:
            HevyAuthError: If authentication fails
            HevyApiError: If request fails
        """
        if not self._session:
            raise HevyApiError("Session not initialized")

        url = f"{API_BASE_URL}{endpoint}"
        headers = {"api-key": self._api_key}

        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with self._session.request(
                    method, url, headers=headers, params=params
                ) as response:
                    if response.status == 401:
                        raise HevyAuthError("Invalid API key")
                    if response.status == 403:
                        raise HevyAuthError("Access forbidden")
                    if response.status >= 400:
                        text = await response.text()
                        raise HevyApiError(
                            f"API request failed with status {response.status}: {text}"
                        )

                    return await response.json()

        except asyncio.TimeoutError as err:
            raise HevyApiError("Request timeout") from err
        except aiohttp.ClientError as err:
            raise HevyApiError(f"Request failed: {err}") from err

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request.

        Returns:
            True if API key is valid

        Raises:
            HevyAuthError: If API key is invalid
            HevyApiError: If request fails
        """
        try:
            await self._request("GET", "/workouts/count")
            return True
        except HevyAuthError:
            raise
        except HevyApiError as err:
            _LOGGER.error("Failed to validate API key: %s", err)
            raise

    async def get_workout_count(self) -> int:
        """Get total workout count.

        Returns:
            Total number of workouts
        """
        data = await self._request("GET", "/workouts/count")
        return data.get("workout_count", 0)

    async def get_workouts(
        self, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:
        """Get paginated workout list.

        Args:
            page: Page number (1-indexed)
            page_size: Number of workouts per page

        Returns:
            Dict with workout data, page info
        """
        params = {"page": page, "pageSize": page_size}
        return await self._request("GET", "/workouts", params=params)

    async def get_workout_events(
        self, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:
        """Get workout events with full exercise and set details.

        Args:
            page: Page number (1-indexed)
            page_size: Number of events per page

        Returns:
            Dict with events array and page info
        """
        params = {"page": page, "pageSize": page_size}
        return await self._request("GET", "/workouts/events", params=params)

    async def get_exercise_templates(self) -> dict[str, Any]:
        """Get exercise template catalog.

        Returns:
            Dict with exercise templates
        """
        return await self._request("GET", "/exercise_templates")

    async def get_routines(self) -> dict[str, Any]:
        """Get saved routines.

        Returns:
            Dict with routine data
        """
        return await self._request("GET", "/routines")

    async def close(self) -> None:
        """Close the session if owned by this client."""
        if self._own_session and self._session:
            await self._session.close()
