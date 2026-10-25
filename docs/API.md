# API Cesar Smart (реверс мобильного приложения)

Всё, что ниже, получено из APK `Cesar Smart` (Android) и проверено на реальном автомобиле.
Это внутренний API, а не публичный. Ничего не гарантируется.

## Авторизация

OAuth2 password / refresh_token, Basic-авторизация клиента:

- Auth URL: `https://tw-sso-authorization-server.csat.ru/tw-sso-authorization-server/oauth/token`
- `grant_type=password`: `username` (телефон), `password`, опционально `device_id`
- `grant_type=refresh_token`: `refresh_token`, опционально `device_id`
- Basic: `client_id` / `client_secret` приложения Cesar Smart; значения в репозитории не
  хранятся — их извлекает `tools/extract_keys.py` из официального APK (или вводятся при
  настройке интеграции).
- Access-токен живёт **120 секунд**, refresh-токен — фактически бессрочный
  (в ответе refresh может прийти новый).

Заголовки приложения (обязательны):

```http
Accept-Language: ru-RU
User-Agent: okhttp/5.1.0
X-CS-TW-APP-TYPE: cesarSmart
X-CS-TW-PLATFORM: ANDROID
X-CS-TW-APP-VERSION: 5.3 (461)
Authorization: Bearer <access_token>
```

## Базовый URL

```
https://tw-cesar-key.csat.ru/
```

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `unit/getSecurityObjectInfo` | Список объектов и `unitId` |
| GET | `unit/statuses/?unitId=<id>` | Все статусы автомобиля |
| GET | `unit/balance?vin=<vin>&unitId=<id>` | Баланс (список объектов `balance`) |
| GET | `unit/location?unitId=<id>` | Координаты, скорость, курс, время |
| GET | `unit/getUnitAvailableCommand?unitId=<id>` | Доступные команды для этой машины |
| GET | `unit/getExecutingCommands?unitId=<id>` | Команды в процессе выполнения |
| POST | `unit/sendCommand` | Тело: `{"unitId": "...", "commandCode": "LOCK_OFF"}` |

401 → обновить access-токен через refresh и повторить запрос один раз.

## Команды

| Код | Действие |
|---|---|
| `REMOTEON` / `REMOTEOFF` | Автозапуск / глушение |
| `LOCK_ON` / `LOCK_OFF` | Запереть / отпереть двери |
| `GUARD_ON` / `GUARD_OFF` | Поставить / снять охрану |
| `BOOT_OPEN` | Открыть багажник (**`BOOT_CLOSE` отсутствует**) |
| `HORN_ON` | Сигнал |
| `LIGHT_ON` | Свет |
| `FINDME_ON` / `FINDME_OFF` | Поиск авто / отмена |
| `POSITION` | Обновить координаты |
| `VALETON` / `VALETOFF` | Сервисный режим вкл/выкл |
| `HEATERON` / `HEATEROFF` | Предпусковой подогреватель (если есть) |
| `WEBASTO_ON` / `WEBASTO_OFF` | Webasto (если есть) |
| `SOS` | Тревога |
| `TEMPguard` | Температурная охрана |

`getUnitAvailableCommand` — источник правды: набор команд зависит от комплектации.
Интеграция строит кнопки только из доступных команд.

## Статусы (пример)

```json
{
  "CAR_LOCK": "CLOSED",
  "ENGINE_STATE": "STOPPED",
  "MODE": "GUARD_MODE_ON",
  "IGNITION": "OFF",
  "DOOR_FRONT_LEFT": "CLOSED",
  "DOOR_FRONT_RIGHT": "CLOSED",
  "DOOR_BACK_LEFT": "CLOSED",
  "DOOR_BACK_RIGHT": "CLOSED",
  "DOOR_BOOT": "CLOSED",
  "FUEL_VALUE": "67.0",
  "FUEL_TYPE": "PERCENT",
  "MILEAGE_KM": "25500",
  "SALON_TEMP": "23",
  "OUTDOOR_TEMP": "26",
  "VEHICLE_CHARGE_VOLT": "12.6",
  "REM_START_BY_PHONE": "",
  "BLE_NUMBER": "..."
}
```

Значения — строки. `CAR_LOCK=CLOSED` означает «заперто». `ENGINE_TEMP` и `SIM1_BALANCE`
часто отсутствуют — это нормально, датчики будут `unknown`.

## Быстрая проверка без Home Assistant

Сначала задайте ключи приложения (их находит `tools/extract_keys.py`):

```bash
export CESAR_CLIENT_ID="..." CESAR_CLIENT_SECRET="..."   # Linux/macOS
$env:CESAR_CLIENT_ID="..."; $env:CESAR_CLIENT_SECRET="..." # PowerShell
```

Дальше:

```bash
python tools/cesar_api.py login --phone +7900... --password '...'
python tools/cesar_api.py units
python tools/cesar_api.py status
python tools/cesar_api.py available
python tools/cesar_api.py cmd LOCK_OFF
python tools/cesar_api.py raw "unit/location?unitId=..." 
```

CLI хранит токены в `cesar_tokens.json` рядом с собой — **не коммитьте этот файл**.
