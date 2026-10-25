from __future__ import annotations

import asyncio

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_BOOT_OPEN
from .coordinator import CesarCoordinator
from .entity import CesarEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    async_add_entities(CesarTrunk(coordinator, unit_id) for unit_id in (coordinator.data or {}))


class CesarTrunk(CesarEntity, CoverEntity):
    _attr_name = "Багажник"
    _attr_icon = "mdi:car-back"
    _attr_supported_features = CoverEntityFeature.OPEN

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_trunk"

    @property
    def is_closed(self) -> bool | None:
        value = self.statuses.get("DOOR_BOOT")
        if value is None:
            return None
        return str(value).upper() == "CLOSED"

    async def async_open_cover(self, **kwargs) -> None:
        await self.coordinator.api.send_command(self._unit_id, CMD_BOOT_OPEN)
        self.hass.async_create_task(self._refresh_later(8))

    async def _refresh_later(self, delay: int) -> None:
        await asyncio.sleep(delay)
        await self.coordinator.async_request_refresh()