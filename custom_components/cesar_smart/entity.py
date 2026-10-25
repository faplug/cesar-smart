from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CesarCoordinator, CesarUnit


class CesarEntity(CoordinatorEntity[CesarCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CesarCoordinator, unit_id: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id

    @property
    def unit(self) -> CesarUnit | None:
        return (self.coordinator.data or {}).get(self._unit_id)

    @property
    def available(self) -> bool:
        return super().available and self.unit is not None

    @property
    def statuses(self) -> dict[str, Any]:
        return self.unit.statuses if self.unit else {}

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self.unit, self._unit_id)


def build_device_info(unit: CesarUnit | None, unit_id: str) -> DeviceInfo:
    obj = unit.obj if unit else {}
    brand = obj.get("brandName") or ""
    model = obj.get("modelName") or ""
    return DeviceInfo(
        identifiers={(DOMAIN, unit_id)},
        manufacturer=MANUFACTURER,
        model=f"{brand} {model}".strip() or None,
        name=unit.name if unit else unit_id,
        serial_number=obj.get("vin"),
        configuration_url="https://www.csat.ru/",
    )
