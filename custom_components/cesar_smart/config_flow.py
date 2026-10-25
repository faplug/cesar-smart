from __future__ import annotations

import logging
import re
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CesarApi, CesarAuthError, CesarConnectionError, CesarError, token_claims
from .const import CLIENT_ID, CLIENT_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CesarConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._client_id = CLIENT_ID
        self._client_secret = CLIENT_SECRET
        self._manual_keys = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._client_id or not self._client_secret:
            return await self.async_step_keys()
        return self._show_menu()

    def _show_menu(self) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=["phone", "token"],
        )

    async def async_step_keys(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = (user_input.get("client_id") or "").strip()
            client_secret = (user_input.get("client_secret") or "").strip()
            if not client_id or not client_secret:
                errors["base"] = "keys_required"
            else:
                self._client_id = client_id
                self._client_secret = client_secret
                self._manual_keys = True
                return self._show_menu()

        return self.async_show_form(
            step_id="keys",
            data_schema=vol.Schema(
                {
                    vol.Required("client_id", default=self._client_id): str,
                    vol.Required("client_secret", default=self._client_secret): str,
                }
            ),
            errors=errors,
        )

    async def _finish(self, uid: str, refresh_token: str, device_id: str | None, title: str) -> ConfigFlowResult:
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()
        data: dict[str, Any] = {"refresh_token": refresh_token, "device_id": device_id}
        if self._manual_keys:
            data["client_id"] = self._client_id
            data["client_secret"] = self._client_secret
        return self.async_create_entry(title=title, data=data)

    async def async_step_phone(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            device_id = str(uuid.uuid4())
            candidates = self._phone_candidates(user_input["phone"])
            payload = None
            for candidate in candidates:
                try:
                    payload = await CesarApi.async_login(
                        session,
                        candidate,
                        user_input["password"],
                        device_id,
                        self._client_id,
                        self._client_secret,
                    )
                    break
                except CesarAuthError:
                    continue
                except CesarConnectionError:
                    errors["base"] = "cannot_connect"
                    break
            if payload is None:
                errors.setdefault("base", "invalid_auth")
            else:
                api = CesarApi(
                    session,
                    payload.get("refresh_token") or "",
                    payload.get("device_id") or device_id,
                    self._client_id,
                    self._client_secret,
                )
                try:
                    await api.async_refresh()
                    objects = await api.get_objects()
                except CesarAuthError:
                    errors["base"] = "invalid_auth"
                except (CesarError, CesarConnectionError):
                    errors["base"] = "cannot_connect"
                else:
                    claims = token_claims(api.access_token or "")
                    uid = claims.get("user_name") or user_input["phone"]
                    if not objects:
                        errors["base"] = "no_objects"
                    else:
                        return await self._finish(uid, api.refresh_token, api.device_id, f"Cesar Smart ({uid[:8]})")

        return self.async_show_form(
            step_id="phone",
            data_schema=vol.Schema(
                {
                    vol.Required("phone"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def _phone_candidates(value: str) -> list[str]:
        value = value.strip()
        candidates = [value]
        digits = re.sub(r"\D", "", value)
        if digits:
            if len(digits) == 11 and digits.startswith("8"):
                digits = "7" + digits[1:]
            candidates.append("+" + digits)
            candidates.append(digits)
        seen: list[str] = []
        for item in candidates:
            if item and item not in seen:
                seen.append(item)
        return seen

    async def async_step_token(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input["refresh_token"].strip()
            device_id = (user_input.get("device_id") or "").strip() or None
            session = async_get_clientsession(self.hass)
            api = CesarApi(session, token, device_id, self._client_id, self._client_secret)
            try:
                await api.async_refresh()
                objects = await api.get_objects()
            except CesarAuthError:
                errors["base"] = "invalid_auth"
            except (CesarError, CesarConnectionError):
                errors["base"] = "cannot_connect"
            else:
                claims = token_claims(api.access_token or "")
                uid = claims.get("user_name") or "account"
                if not objects:
                    errors["base"] = "no_objects"
                else:
                    return await self._finish(uid, api.refresh_token, api.device_id, f"Cesar Smart ({uid[:8]})")

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema(
                {
                    vol.Required("refresh_token"): str,
                    vol.Optional("device_id"): str,
                }
            ),
            errors=errors,
        )
