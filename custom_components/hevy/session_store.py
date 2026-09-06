from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.file import write_utf8_file_atomic


class SessionStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.path = Path(hass.config.path(".storage", f"hevy.workout.{entry_id}"))

    def _load(self) -> dict[str, Any] | None:
        try:
            saved = json.loads(self.path.read_text())
        except FileNotFoundError:
            return None
        if not isinstance(saved, dict) or saved.get("version") != 1:
            raise HomeAssistantError(
                "The saved Hevy workout has an unsupported format."
            )
        if not isinstance(saved.get("data"), dict) or "session" not in saved["data"]:
            raise HomeAssistantError("The saved Hevy workout could not be read.")
        return saved["data"]

    async def async_load(self) -> dict[str, Any] | None:
        return await self.hass.async_add_executor_job(self._load)

    def _write(self, data: dict[str, Any]) -> None:
        encoded = json.dumps({"version": 1, "data": data}, allow_nan=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_utf8_file_atomic(str(self.path), encoded, private=True)

    async def async_save(self, data: dict[str, Any]) -> None:
        await self.hass.async_add_executor_job(self._write, data)
