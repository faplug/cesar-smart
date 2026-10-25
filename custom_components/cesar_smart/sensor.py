from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CesarCoordinator, CesarUnit
from .entity import CesarEntity


def _num(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


@dataclass(frozen=True, kw_only=True)
class CesarSensorDescription(SensorEntityDescription):
    value_fn: Callable[[CesarUnit], Any] = lambda unit: None
    unit_fn: Callable[[CesarUnit], str | None] | None = None


SENSORS: tuple[CesarSensorDescription, ...] = (
    CesarSensorDescription(
        key="fuel",
        name="Топливо",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.statuses.get("FUEL_VALUE")),
        unit_fn=lambda unit: "L" if unit.statuses.get("FUEL_TYPE") == "LITERS" else PERCENTAGE,
    ),
    CesarSensorDescription(
        key="mileage",
        name="Пробег",
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda unit: _num(unit.statuses.get("MILEAGE_KM")),
    ),
    CesarSensorDescription(
        key="engine_temp",
        name="Температура двигателя",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.statuses.get("ENGINE_TEMP")),
    ),
    CesarSensorDescription(
        key="salon_temp",
        name="Температура в салоне",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.statuses.get("SALON_TEMP")),
    ),
    CesarSensorDescription(
        key="outdoor_temp",
        name="Температура на улице",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.statuses.get("OUTDOOR_TEMP")),
    ),
    CesarSensorDescription(
        key="battery_voltage",
        name="Напряжение АКБ",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.statuses.get("VEHICLE_CHARGE_VOLT")),
    ),
    CesarSensorDescription(
        key="sim_balance",
        name="Баланс SIM",
        icon="mdi:sim",
        native_unit_of_measurement="₽",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda unit: _num(unit.statuses.get("SIM1_BALANCE")),
        entity_registry_enabled_default=False,
    ),
    CesarSensorDescription(
        key="account_balance",
        name="Баланс счёта",
        icon="mdi:cash",
        native_unit_of_measurement="₽",
        value_fn=lambda unit: unit.balance,
    ),
    CesarSensorDescription(
        key="speed",
        name="Скорость",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda unit: _num(unit.location.get("speedKm")) if unit.location else None,
    ),
    CesarSensorDescription(
        key="location_time",
        name="Время определения",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda unit: _parse_dt(unit.location.get("date")) if unit.location else None,
    ),
)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    entities = []
    for unit_id in (coordinator.data or {}):
        for description in SENSORS:
            entities.append(CesarSensor(coordinator, unit_id, description))
    async_add_entities(entities)


class CesarSensor(CesarEntity, SensorEntity):
    entity_description: CesarSensorDescription

    def __init__(
        self, coordinator: CesarCoordinator, unit_id: str, description: CesarSensorDescription
    ) -> None:
        super().__init__(coordinator, unit_id)
        self.entity_description = description
        self._attr_unique_id = f"{unit_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        if not self.unit:
            return None
        return self.entity_description.value_fn(self.unit)

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit_fn = self.entity_description.unit_fn
        if unit_fn and self.unit:
            return unit_fn(self.unit)
        return self.entity_description.native_unit_of_measurement