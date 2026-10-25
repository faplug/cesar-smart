from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any

import aiohttp

from .const import APP_HEADERS, AUTH_URL, BASE_URL

_LOGGER = logging.getLogger(__name__)


class CesarError(Exception):
    """Base error."""


class CesarAuthError(CesarError):
    """Auth failed."""


class CesarConnectionError(CesarError):
    """Network/API failed."""


def _basic(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def token_claims(token: str) -> dict[str, Any]:
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))
    except Exception:
        return {}


class CesarApi:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str,
        device_id: str | None,
        client_id: str,
        client_secret: str,
        token_updated=None,
    ) -> None:
        self._session = session
        self._refresh_token = refresh_token
        self._device_id = device_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_updated = token_updated
        self._access_token: str | None = None
        self._expires_at = 0.0

    @property
    def device_id(self) -> str | None:
        return self._device_id

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    @staticmethod
    async def async_login(
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        device_id: str | None,
        client_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        data = {"grant_type": "password", "username": username, "password": password}
        if device_id:
            data["device_id"] = device_id
        try:
            async with session.post(
                AUTH_URL,
                data=data,
                headers={
                    "Authorization": _basic(client_id, client_secret),
                    "Accept-Language": "ru-RU",
                    "User-Agent": "okhttp/5.1.0",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise CesarAuthError(f"HTTP {resp.status}: {text[:200]}")
                return json.loads(text)
        except aiohttp.ClientError as err:
            raise CesarConnectionError(str(err)) from err

    async def async_refresh(self) -> None:
        data = {"grant_type": "refresh_token", "refresh_token": self._refresh_token}
        if self._device_id:
            data["device_id"] = self._device_id
        try:
            async with self._session.post(
                AUTH_URL,
                data=data,
                headers={
                    "Authorization": _basic(self._client_id, self._client_secret),
                    "Accept-Language": "ru-RU",
                    "User-Agent": "okhttp/5.1.0",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                if resp.status in (400, 401):
                    raise CesarAuthError(f"refresh rejected: HTTP {resp.status} {text[:200]}")
                if resp.status != 200:
                    raise CesarConnectionError(f"refresh HTTP {resp.status}: {text[:200]}")
                payload = json.loads(text)
        except aiohttp.ClientError as err:
            raise CesarConnectionError(str(err)) from err

        self._access_token = payload.get("access_token")
        if not self._access_token:
            raise CesarAuthError("no access_token in refresh response")
        self._expires_at = time.time() + int(payload.get("expires_in") or 120) - 20
        if payload.get("refresh_token"):
            self._refresh_token = payload["refresh_token"]
        if payload.get("device_id"):
            self._device_id = payload["device_id"]
        if self._token_updated:
            self._token_updated(self._refresh_token, self._device_id)

    async def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._expires_at:
            await self.async_refresh()

    async def _request(self, method: str, path: str, payload: Any | None = None, retry: bool = True) -> Any:
        await self._ensure_token()
        headers = dict(APP_HEADERS)
        headers["Authorization"] = f"Bearer {self._access_token}"
        data = None
        if payload is not None:
            data = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        try:
            async with self._session.request(
                method,
                BASE_URL + path,
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                if resp.status == 401 and retry:
                    await self.async_refresh()
                    return await self._request(method, path, payload, retry=False)
                if resp.status >= 400:
                    raise CesarError(f"HTTP {resp.status} on {path}: {text[:200]}")
                return json.loads(text) if text else None
        except aiohttp.ClientError as err:
            raise CesarConnectionError(str(err)) from err

    async def get_objects(self) -> list[dict[str, Any]]:
        return await self._request("GET", "unit/getSecurityObjectInfo") or []

    async def get_statuses(self, unit_id: str) -> dict[str, Any]:
        return await self._request("GET", f"unit/statuses/?unitId={unit_id}") or {}

    async def get_balance(self, vin: str, unit_id: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"unit/balance?vin={vin}&unitId={unit_id}") or []

    async def get_location(self, unit_id: str) -> dict[str, Any]:
        return await self._request("GET", f"unit/location?unitId={unit_id}") or {}

    async def get_available(self, unit_id: str) -> list[str]:
        return await self._request("GET", f"unit/getUnitAvailableCommand?unitId={unit_id}") or []

    async def get_executing(self, unit_id: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"unit/getExecutingCommands?unitId={unit_id}") or []

    async def send_command(self, unit_id: str, code: str) -> None:
        await self._request("POST", "unit/sendCommand", {"unitId": unit_id, "commandCode": code})

    async def gather_unit(self, vin: str, unit_id: str) -> dict[str, Any]:
        statuses, balance, location, available, executing = await asyncio.gather(
            self.get_statuses(unit_id),
            self.get_balance(vin, unit_id),
            self.get_location(unit_id),
            self.get_available(unit_id),
            self.get_executing(unit_id),
            return_exceptions=True,
        )

        def ok(value, default):
            if isinstance(value, Exception):
                _LOGGER.debug("unit %s partial failure: %s", unit_id, value)
                return default
            return value

        bal = 0.0
        for row in ok(balance, []):
            for item in row.get("balance") or []:
                try:
                    bal += float(item.get("balance") or 0)
                except (TypeError, ValueError):
                    pass

        return {
            "statuses": ok(statuses, {}),
            "balance": bal if ok(balance, []) else None,
            "location": ok(location, {}),
            "available": ok(available, []),
            "executing": ok(executing, []),
        }
