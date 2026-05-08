# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SN-print** — Telegram-бот на Python 3.11, генерирует QR-коды и штрихкоды (Code128) из серийных номеров.
Virtual environment is in `.venv/` (excluded from version control).

- GitHub: https://github.com/Shura4eburek/SN-print
- Деплой: Railway (webhook-режим)
- Webapp: GitHub Pages — https://shura4eburek.github.io/SN-print/webapp/

## Файловая структура

| Файл | Документация | Назначение |
|---|---|---|
| `bot.py` | [docs/bot.md](docs/bot.md) | Точка входа, хендлеры Telegram |
| `generator.py` | [docs/generator.md](docs/generator.md) | Генерация PNG (QR + Code128) |
| `metricon_client.py` | [docs/metricon.md](docs/metricon.md) | Клиент мониторинга Metricon |
| `webapp/index.html` | [docs/webapp-index.md](docs/webapp-index.md) | Mini App для печати QR/barcode |
| `webapp/util.html` | [docs/webapp-util.md](docs/webapp-util.md) | Mini App для наклейки утиля |
| `requirements.txt` | — | Зависимости |
| `.env` | — | Секреты (не в git) |

## Переменные окружения (.env)

```
BOT_TOKEN=...
WEBAPP_URL=https://shura4eburek.github.io/SN-print/webapp/
WEBHOOK_URL=https://xxx.up.railway.app   # Railway URL
METRICON_API_KEY=...                     # ключ для Metricon
METRICON_URL=https://web-production-37313.up.railway.app  # можно переопределить
# PORT выставляет Railway автоматически
```

## Ключевые факты

- Webhook если `PORT` + `WEBHOOK_URL` заданы, иначе polling
- `requirements.txt` должен содержать `python-telegram-bot[webhooks]` (не просто `python-telegram-bot`)
- Metricon: вызовы синхронные (`track_request`, `track_error`), клиент сам отправляет в daemon-тредах
- `metricon_client.py` не изменять без явной просьбы — может автообновляться с сервера

## Railway

- `Procfile`: `web: python bot.py`
- `.python-version`: `3.11`
- Переменные: `BOT_TOKEN`, `WEBAPP_URL`, `WEBHOOK_URL`, `METRICON_API_KEY` (PORT — автоматически)

## Environment

```bash
source .venv/Scripts/activate  # Windows (bash)
```

## Common Commands

```bash
python bot.py             # запуск локально (polling)
python -m pytest          # тесты
python -m ruff check .    # lint
```
