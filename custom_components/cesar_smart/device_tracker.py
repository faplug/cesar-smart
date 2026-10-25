from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CesarCoordinator
from .entity import CesarEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    async_add_entities(CesarTracker(coordinator, unit_id) for unit_id in (coordinator.data or {}))


class CesarTracker(CesarEntity, TrackerEntity):
    _attr_name = "Местоположение"
    _attr_icon = "mdi:map-marker"

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_tracker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        if not self.unit or not self.unit.location:
            return None
        try:
            return float(self.unit.location["latitude"])
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def longitude(self) -> float | None:
        if not self.unit or not self.unit.location:
            return None
        try:
            return float(self.unit.location["longitude"])
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.unit or not self.unit.location:
            return None
        location = self.unit.location
        return {
            "speed_kmh": location.get("speedKm"),
            "course": location.get("course"),
            "updated": location.get("date"),
        }
