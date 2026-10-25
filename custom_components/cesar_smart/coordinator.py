from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CesarApi, CesarAuthError, CesarConnectionError, CesarError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class CesarUnit:
    obj: dict[str, Any]
    unit: dict[str, Any]
    statuses: dict[str, Any] = field(default_factory=dict)
    balance: float | None = None
    location: dict[str, Any] = field(default_factory=dict)
    available: list[str] = field(default_factory=list)
    executing: list[dict[str, Any]] = field(default_factory=list)

    @property
    def unit_id(self) -> str:
        return self.unit["unitId"]

    @property
    def vin(self) -> str:
        return self.obj.get("vin") or ""

    @property
    def name(self) -> str:
        parts = [self.obj.get("brandName"), self.obj.get("modelName")]
        label = " ".join(p for p in parts if p) or self.obj.get("vin") or self.unit_id
        plate = self.obj.get("plateNumber")
        return f"{label} {plate}".strip() if plate else label


type CesarData = dict[str, CesarUnit]


class CesarCoordinator(DataUpdateCoordinator[CesarData]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: CesarApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> CesarData:
        try:
            objects = await self.api.get_objects()
        except CesarAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (CesarError, CesarConnectionError) as err:
            raise UpdateFailed(str(err)) from err

        units: CesarData = {}
        for obj in objects:
            for unit in obj.get("units") or []:
                unit_id = unit.get("unitId")
                if not unit_id:
                    continue
                try:
                    payload = await self.api.gather_unit(obj.get("vin") or "", unit_id)
                except CesarAuthError as err:
                    raise ConfigEntryAuthFailed(str(err)) from err
                except CesarError as err:
                    _LOGGER.warning("Unit %s update failed: %s", unit_id, err)
                    continue
                units[unit_id] = CesarUnit(obj=obj, unit=unit, **payload)
        return units
