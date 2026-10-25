from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_BUTTONS
from .coordinator import CesarCoordinator
from .entity import CesarEntity

_LOGGER = logging.getLogger(__name__)

HANDLED_BY_ENTITIES = {"LOCK_ON", "LOCK_OFF", "GUARD_ON", "GUARD_OFF"}
DIAGNOSTIC_CODES = {"POSITION"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    entities: list[ButtonEntity] = []
    for unit_id, unit in (coordinator.data or {}).items():
        entities.append(CesarRefreshButton(coordinator, unit_id))
        for code in unit.available:
            if code in HANDLED_BY_ENTITIES:
                continue
            if code in COMMAND_BUTTONS:
                entities.append(CesarCommandButton(coordinator, unit_id, code))
            else:
                _LOGGER.debug("Unmapped command %s for %s", code, unit_id)
    async_add_entities(entities)


class CesarRefreshButton(CesarEntity, ButtonEntity):
    _attr_name = "Обновить данные"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_refresh"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class CesarCommandButton(CesarEntity, ButtonEntity):
    def __init__(self, coordinator: CesarCoordinator, unit_id: str, code: str) -> None:
        super().__init__(coordinator, unit_id)
        self._code = code
        name, icon = COMMAND_BUTTONS[code]
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{unit_id}_cmd_{code.lower()}"
        if code in DIAGNOSTIC_CODES:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        await self.coordinator.api.send_command(self._unit_id, self._code)
        self.hass.async_create_task(self._refresh_later())

    async def _refresh_later(self) -> None:
        await asyncio.sleep(8)
        await self.coordinator.async_request_refresh()