from datetime import timedelta

DOMAIN = "cesar_smart"

BASE_URL = "https://tw-cesar-key.csat.ru/"
AUTH_URL = "https://tw-sso-authorization-server.csat.ru/tw-sso-authorization-server/oauth/token"

try:
    from .const_local import CLIENT_ID, CLIENT_SECRET
except ImportError:
    CLIENT_ID = ""
    CLIENT_SECRET = ""

APP_HEADERS = {
    "Accept-Language": "ru-RU",
    "User-Agent": "okhttp/5.1.0",
    "X-CS-TW-APP-TYPE": "cesarSmart",
    "X-CS-TW-PLATFORM": "ANDROID",
    "X-CS-TW-APP-VERSION": "5.3 (461)",
}

MANUFACTURER = "Cesar Satellite"
MODEL = "Cesar Smart"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=120)

CMD_ENGINE_ON = "REMOTEON"
CMD_ENGINE_OFF = "REMOTEOFF"
CMD_LOCK_ON = "LOCK_ON"
CMD_LOCK_OFF = "LOCK_OFF"
CMD_GUARD_ON = "GUARD_ON"
CMD_GUARD_OFF = "GUARD_OFF"
CMD_BOOT_OPEN = "BOOT_OPEN"

COMMAND_BUTTONS = {
    "GUARD_ON": ("Охрана включить", "mdi:shield-lock"),
    "GUARD_OFF": ("Охрана выключить", "mdi:shield-off"),
    "LOCK_ON": ("Замок закрыть", "mdi:lock"),
    "LOCK_OFF": ("Замок открыть", "mdi:lock-open"),
    "FINDME_ON": ("Найти авто", "mdi:bullhorn"),
    "FINDME_OFF": ("Отменить поиск", "mdi:bullhorn-outline"),
    "HORN_ON": ("Сигнал", "mdi:car-horn"),
    "LIGHT_ON": ("Свет", "mdi:car-light-high"),
    "BOOT_OPEN": ("Багажник", "mdi:car-back"),
    "POSITION": ("Обновить координаты", "mdi:crosshairs-gps"),
    "VALETON": ("Сервисный режим включить", "mdi:account-key"),
    "VALETOFF": ("Сервисный режим выключить", "mdi:account-key-outline"),
    "HEATERON": ("Подогреватель включить", "mdi:radiator"),
    "HEATEROFF": ("Подогреватель выключить", "mdi:radiator-off"),
    "WEBASTO_ON": ("Webasto включить", "mdi:radiator"),
    "WEBASTO_OFF": ("Webasto выключить", "mdi:radiator-off"),
    "SOS": ("SOS", "mdi:alarm-light"),
    "TEMPguard": ("Температурная охрана", "mdi:thermometer-alert"),
}
