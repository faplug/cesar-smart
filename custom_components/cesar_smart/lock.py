from __future__ import annotations

import asyncio

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_LOCK_OFF, CMD_LOCK_ON
from .coordinator import CesarCoordinator
from .entity import CesarEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    async_add_entities(CesarLock(coordinator, unit_id) for unit_id in (coordinator.data or {}))


class CesarLock(CesarEntity, LockEntity):
    _attr_name = "Центральный замок"
    _attr_icon = "mdi:car-door-lock"

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_lock"

    @property
    def is_locked(self) -> bool | None:
        value = self.statuses.get("CAR_LOCK")
        if value is None:
            return None
        return str(value).upper() != "OPEN"

    async def _send(self, code: str, delay: int = 8) -> None:
        await self.coordinator.api.send_command(self._unit_id, code)
        self.hass.async_create_task(self._refresh_later(delay))

    async def _refresh_later(self, delay: int) -> None:
        await asyncio.sleep(delay)
        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs) -> None:
        await self._send(CMD_LOCK_ON)

    async def async_unlock(self, **kwargs) -> None:
        await self._send(CMD_LOCK_OFF)