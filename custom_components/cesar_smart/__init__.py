from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import CesarApi
from .const import CLIENT_ID, CLIENT_SECRET, DOMAIN
from .coordinator import CesarCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.LOCK,
    Platform.COVER,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.IMAGE,
]

type CesarConfigEntry = ConfigEntry[CesarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CesarConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
    saved = await store.async_load() or {}

    refresh_token = saved.get("refresh_token") or entry.data["refresh_token"]
    device_id = saved.get("device_id") or entry.data.get("device_id")

    def _save_tokens(new_refresh: str, new_device: str | None) -> None:
        hass.async_create_task(
            store.async_save({"refresh_token": new_refresh, "device_id": new_device})
        )

    client_id = entry.data.get("client_id") or CLIENT_ID
    client_secret = entry.data.get("client_secret") or CLIENT_SECRET
    if not client_id or not client_secret:
        raise ConfigEntryError("Не заданы ключи приложения Cesar (client_id/client_secret)")

    api = CesarApi(
        session,
        refresh_token,
        device_id,
        client_id,
        client_secret,
        _save_tokens,
    )
    coordinator = CesarCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CesarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
