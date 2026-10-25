from __future__ import annotations

from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CesarCoordinator
from .entity import build_device_info

CAR_IMAGE = Path(__file__).parent / "car.png"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    async_add_entities(
        CesarCarImage(coordinator, unit_id) for unit_id in (coordinator.data or {})
    )


class CesarCarImage(ImageEntity):
    _attr_has_entity_name = True
    _attr_name = "Автомобиль"
    _attr_icon = "mdi:car"
    _attr_content_type = "image/png"

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator.hass)
        self.coordinator = coordinator
        self._unit_id = unit_id
        self._attr_unique_id = f"{unit_id}_photo"

    @property
    def device_info(self):
        return build_device_info((self.coordinator.data or {}).get(self._unit_id), self._unit_id)

    async def async_image(self) -> bytes | None:
        if not CAR_IMAGE.is_file():
            return None
        return CAR_IMAGE.read_bytes()
