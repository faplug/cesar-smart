from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CesarCoordinator, CesarUnit
from .entity import CesarEntity


@dataclass(frozen=True, kw_only=True)
class CesarBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[CesarUnit], bool | None] = lambda unit: None


def _status_is(key: str, expected: str) -> Callable[[CesarUnit], bool | None]:
    def getter(unit: CesarUnit) -> bool | None:
        value = unit.statuses.get(key)
        if value is None:
            return None
        return str(value).upper() == expected

    return getter


def _door(key: str) -> Callable[[CesarUnit], bool | None]:
    def getter(unit: CesarUnit) -> bool | None:
        value = unit.statuses.get(key)
        if value is None:
            return None
        return str(value).upper() != "CLOSED"

    return getter


def _flag(key: str) -> Callable[[CesarUnit], bool | None]:
    def getter(unit: CesarUnit) -> bool | None:
        value = unit.statuses.get(key)
        if value is None:
            return None
        return str(value).upper() not in ("", "0", "FALSE", "OFF", "NONE")

    return getter


BINARY_SENSORS: tuple[CesarBinaryDescription, ...] = (
    CesarBinaryDescription(
        key="engine_running",
        name="Двигатель работает",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:engine",
        value_fn=_status_is("ENGINE_STATE", "RUNNING"),
    ),
    CesarBinaryDescription(
        key="ignition",
        name="Зажигание",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:key-variant",
        value_fn=_status_is("IGNITION", "ON"),
    ),
    CesarBinaryDescription(
        key="armed",
        name="Охрана",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=_status_is("MODE", "GUARD_MODE_ON"),
    ),
    CesarBinaryDescription(
        key="car_lock",
        name="Замки заперты",
        device_class=BinarySensorDeviceClass.LOCK,
        value_fn=_status_is("CAR_LOCK", "CLOSED"),
    ),
    CesarBinaryDescription(
        key="door_front_left",
        name="Дверь передняя левая",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door("DOOR_FRONT_LEFT"),
    ),
    CesarBinaryDescription(
        key="door_front_right",
        name="Дверь передняя правая",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door("DOOR_FRONT_RIGHT"),
    ),
    CesarBinaryDescription(
        key="door_back_left",
        name="Дверь задняя левая",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door("DOOR_BACK_LEFT"),
    ),
    CesarBinaryDescription(
        key="door_back_right",
        name="Дверь задняя правая",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door("DOOR_BACK_RIGHT"),
    ),
    CesarBinaryDescription(
        key="door_boot",
        name="Багажник",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door("DOOR_BOOT"),
    ),
    CesarBinaryDescription(
        key="rem_start_by_phone",
        name="Автозапуск с телефона",
        icon="mdi:cellphone-arrow-down",
        value_fn=_flag("REM_START_BY_PHONE"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CesarCoordinator = entry.runtime_data
    entities = []
    for unit_id in (coordinator.data or {}):
        for description in BINARY_SENSORS:
            entities.append(CesarBinarySensor(coordinator, unit_id, description))
    async_add_entities(entities)


class CesarBinarySensor(CesarEntity, BinarySensorEntity):
    entity_description: CesarBinaryDescription

    def __init__(
        self, coordinator: CesarCoordinator, unit_id: str, description: CesarBinaryDescription
    ) -> None:
        super().__init__(coordinator, unit_id)
        self.entity_description = description
        self._attr_unique_id = f"{unit_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        if not self.unit:
            return None
        return self.entity_description.value_fn(self.unit)