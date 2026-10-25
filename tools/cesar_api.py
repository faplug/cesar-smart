import argparse
import base64
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://tw-cesar-key.csat.ru/"
AUTH = "https://tw-sso-authorization-server.csat.ru/tw-sso-authorization-server/oauth/token"

HERE = Path(__file__).resolve().parent
TOKENS = HERE / "cesar_tokens.json"
UNITS = HERE / "cesar_units.json"

HEADERS = {
    "Accept-Language": "ru-RU",
    "User-Agent": "okhttp/5.1.0",
    "X-CS-TW-APP-TYPE": "cesarSmart",
    "X-CS-TW-PLATFORM": "ANDROID",
    "X-CS-TW-APP-VERSION": "5.3 (461)",
}


def basic() -> str:
    client_id = os.environ.get("CESAR_CLIENT_ID", "")
    client_secret = os.environ.get("CESAR_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        sys.exit("set CESAR_CLIENT_ID/CESAR_CLIENT_SECRET (see tools/extract_keys.py)")
    return "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()


def http(url, data=None, headers=None, method="GET", timeout=30):
    hdrs = dict(HEADERS)
    hdrs["Accept"] = "application/json"
    if headers:
        hdrs.update(headers)
    body = None
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = data.encode() if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def save(tok: dict) -> None:
    TOKENS.write_text(json.dumps(tok, indent=1), encoding="utf-8")


def load() -> dict:
    if not TOKENS.exists():
        sys.exit("no tokens: run login first")
    return json.loads(TOKENS.read_text(encoding="utf-8"))


def exp_info(token: str) -> str:
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        d = json.loads(base64.urlsafe_b64decode(p))
        left = int(d.get("exp", 0)) - int(time.time())
        return f"exp in {left}s"
    except Exception:
        return "exp ?"


def refresh() -> dict:
    t = load()
    data = {"grant_type": "refresh_token", "refresh_token": t.get("refresh_token", "")}
    if t.get("device_id"):
        data["device_id"] = t["device_id"]
    st, txt = http(AUTH, data, {"Authorization": basic()}, "POST")
    if st != 200:
        sys.exit(f"refresh failed: HTTP {st} {txt[:300]}")
    tok = json.loads(txt)
    if not tok.get("device_id"):
        tok["device_id"] = t.get("device_id")
    save(tok)
    print("refreshed,", exp_info(tok["access_token"]), file=sys.stderr)
    return tok


def api(path, payload=None, method="GET", retry=True):
    t = load()
    hdrs = {"Authorization": "Bearer " + t["access_token"]}
    data = None
    if payload is not None:
        data = json.dumps(payload)
        hdrs["Content-Type"] = "application/json"
    st, txt = http(BASE + path, data, hdrs, method)
    if st == 401 and retry:
        refresh()
        return api(path, payload, method, retry=False)
    return st, txt


def login(phone, password, device_id=None):
    data = {"grant_type": "password", "username": phone, "password": password}
    if device_id:
        data["device_id"] = device_id
    st, txt = http(AUTH, data, {"Authorization": basic()}, "POST")
    if st != 200:
        sys.exit(f"login failed: HTTP {st} {txt[:400]}")
    tok = json.loads(txt)
    save(tok)
    print("logged in,", exp_info(tok["access_token"]), file=sys.stderr)


def units():
    st, txt = api("unit/getSecurityObjectInfo")
    if st != 200:
        sys.exit(f"HTTP {st} {txt[:400]}")
    ids = []
    for obj in json.loads(txt):
        for u in obj.get("units", []):
            ids.append(u["unitId"])
            print(obj.get("vin"), obj.get("brandName"), obj.get("modelName"), "| unit:", u["unitId"], u["unitClass"])
    UNITS.write_text(json.dumps(ids), encoding="utf-8")


def current_unit(explicit=None):
    if explicit:
        return explicit
    if UNITS.exists():
        ids = json.loads(UNITS.read_text(encoding="utf-8"))
        if len(ids) == 1:
            return ids[0]
        if len(ids) > 1:
            sys.exit("several units, use --unit: " + ", ".join(ids))
    t = load()
    return t.get("unit_id") or sys.exit("no unit id, run units or pass --unit")


def status(unit):
    st, txt = api(f"unit/statuses/?unitId={unit}")
    print("HTTP", st)
    print(txt[:2000])


def state(unit):
    st, txt = api(f"unit/statuses/?unitId={unit}")
    if st != 200:
        print("UNKNOWN")
        return
    try:
        print(json.loads(txt).get("ENGINE_STATE") or "UNKNOWN")
    except Exception:
        print("UNKNOWN")


def available(unit):
    st, txt = api(f"unit/getUnitAvailableCommand?unitId={unit}")
    print("HTTP", st, txt[:1200])


def send(code: str, unit: str):
    st, txt = api("unit/sendCommand", {"unitId": unit, "commandCode": code}, "POST")
    print(f"{code} -> HTTP {st} {txt[:400]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("login")
    p.add_argument("--phone", default=os.environ.get("CESAR_PHONE"))
    p.add_argument("--password")
    p.add_argument("--device-id")

    sub.add_parser("refresh")
    sub.add_parser("units")
    sub.add_parser("status")
    sub.add_parser("state")
    sub.add_parser("available")
    sub.add_parser("on")
    sub.add_parser("off")

    c = sub.add_parser("cmd")
    c.add_argument("code")

    for name in ("status", "state", "available", "on", "off", "cmd"):
        sub.choices[name].add_argument("--unit", default=None)

    r = sub.add_parser("raw")
    r.add_argument("path")
    r.add_argument("--body", default=None)
    r.add_argument("--post", action="store_true")

    a = ap.parse_args()

    if a.cmd == "login":
        login(a.phone or input("phone (+7...): ").strip(), a.password or getpass.getpass("password: "), a.device_id)
    elif a.cmd == "refresh":
        refresh()
    elif a.cmd == "units":
        units()
    elif a.cmd == "status":
        status(current_unit(a.unit))
    elif a.cmd == "state":
        state(current_unit(a.unit))
    elif a.cmd == "available":
        available(current_unit(a.unit))
    elif a.cmd == "on":
        send("REMOTEON", current_unit(a.unit))
    elif a.cmd == "off":
        send("REMOTEOFF", current_unit(a.unit))
    elif a.cmd == "cmd":
        send(a.code, current_unit(a.unit))
    elif a.cmd == "raw":
        payload = json.loads(a.body) if a.body else None
        st, txt = api(a.path, payload, "POST" if a.post else "GET")
        print("HTTP", st)
        print(txt[:3000])


if __name__ == "__main__":
    main()
