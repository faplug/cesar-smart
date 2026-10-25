from __future__ import annotations

import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_ENGINE_OFF, CMD_ENGINE_ON, CMD_GUARD_OFF, CMD_GUARD_ON
from .coordinator import CesarCoordinator
from .entity import CesarEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = []
    for unit_id in (coordinator.data or {}):
        entities.append(CesarEngineSwitch(coordinator, unit_id))
        entities.append(CesarGuardSwitch(coordinator, unit_id))
    async_add_entities(entities)


class CesarSwitchBase(CesarEntity, SwitchEntity):
    async def _send(self, code: str, delay: int) -> None:
        await self.coordinator.api.send_command(self._unit_id, code)
        self.hass.async_create_task(self._refresh_later(delay))

    async def _refresh_later(self, delay: int) -> None:
        await asyncio.sleep(delay)
        await self.coordinator.async_request_refresh()


class CesarEngineSwitch(CesarSwitchBase):
    _attr_name = "Двигатель"
    _attr_icon = "mdi:car-key"

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_engine"

    @property
    def is_on(self) -> bool:
        return str(self.statuses.get("ENGINE_STATE", "")).upper() == "RUNNING"

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(CMD_ENGINE_ON, 18)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(CMD_ENGINE_OFF, 10)


class CesarGuardSwitch(CesarSwitchBase):
    _attr_name = "Охрана"
    _attr_icon = "mdi:shield-car"

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_guard"

    @property
    def is_on(self) -> bool:
        return str(self.statuses.get("MODE", "")).upper() == "GUARD_MODE_ON"

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(CMD_GUARD_ON, 8)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(CMD_GUARD_OFF, 8)