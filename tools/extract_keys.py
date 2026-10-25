"""Извлекает client_id/client_secret приложения Cesar Smart из официального APK.

Ключи не входят в поставку интеграции. Скрипт читает строки из classes*.dex и
проверяет пары на сервере авторизации Cesar: верная пара получает ответ
"invalid_grant" (клиент авторизован, пользователь заведомо неверный), неверная — 401.

Пример:
    python tools/extract_keys.py "Cesar Smart.apk"
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

AUTH_URL = "https://tw-sso-authorization-server.csat.ru/tw-sso-authorization-server/oauth/token"
SECRET_RE = re.compile(r"^[A-Za-z]{1,6}\d{6,14}$")


def dex_strings(path: str):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".dex"):
                continue
            data = archive.read(name)
            strings = {
                match.group().decode("ascii", "replace")
                for match in re.finditer(rb"[\x20-\x7e]{4,}", data)
            }
            yield name, strings


def probe(client_id: str, client_secret: str) -> bool:
    raw = f"{client_id}:{client_secret}".encode()
    headers = {
        "Authorization": "Basic " + base64.b64encode(raw).decode(),
        "Accept-Language": "ru-RU",
        "User-Agent": "okhttp/5.1.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = urllib.parse.urlencode(
        {"grant_type": "password", "username": "probe@example.com", "password": "probe"}
    ).encode()
    request = urllib.request.Request(AUTH_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20):
            return False
    except urllib.error.HTTPError as error:
        if error.code == 400:
            return True
        if error.code == 401:
            return False
        raise SystemExit(f"unexpected HTTP {error.code} from Cesar auth server")
    except OSError as error:
        raise SystemExit(f"network error: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Cesar Smart OAuth keys from an APK")
    parser.add_argument("apk", help="path to the Cesar Smart APK")
    args = parser.parse_args()

    found = False
    for name, strings in dex_strings(args.apk):
        client_ids = sorted(s for s in strings if "cesar" in s.lower() and s.endswith("_key"))
        secrets = sorted(s for s in strings if SECRET_RE.match(s))
        if not client_ids or not secrets:
            continue
        for client_id in client_ids:
            for secret in secrets:
                if probe(client_id, secret):
                    print(f"client_id:     {client_id}")
                    print(f"client_secret: {secret}")
                    print(f"(dex: {name})")
                    found = True

    if not found:
        print("Не удалось подобрать ключи автоматически.", file=sys.stderr)
        print("Введите client_id/client_secret вручную при добавлении интеграции.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
