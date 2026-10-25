# Cesar Smart — правила проекта

- Интеграция Home Assistant на Python; домен `cesar_smart`; версия 1.3.0.
- Глобальные правила: `~/.config/opencode/AGENTS.md` (кодировка, секреты, план + diff).
- Секреты и личные данные (`cesar_tokens.json`, `cesar_units.json`, VIN/unitId) — не коммитить (уже в `.gitignore`).
- Проверка: `python -m compileall custom_components/cesar_smart tools`.
- Структура для HACS: `custom_components/cesar_smart`, `hacs.json`; документация — `README.md`, `docs/`.
