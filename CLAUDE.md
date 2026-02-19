# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SN-print** — Telegram-бот на Python 3.11, генерирует QR-коды и штрихкоды (Code128) из серийных номеров.
Virtual environment is in `.venv/` (excluded from version control).

- GitHub: https://github.com/Shura4eburek/SN-print
- Деплой: Railway (webhook-режим)
- Webapp: GitHub Pages — https://shura4eburek.github.io/SN-print/webapp/

## Файловая структура

| Файл | Назначение |
|---|---|
| `bot.py` | Точка входа, хендлеры Telegram |
| `generator.py` | Генерация PNG (QR + Code128, 900px, серийник под кодом) |
| `webapp/index.html` | Mini App для печати (QR/Barcode, размер, CSS @page) |
| `requirements.txt` | Зависимости |
| `.env` | Секреты (не в git) |

## Переменные окружения (.env)

```
BOT_TOKEN=...
WEBAPP_URL=https://shura4eburek.github.io/SN-print/webapp/
WEBHOOK_URL=https://xxx.up.railway.app   # Railway URL
# PORT выставляет Railway автоматически
```

## Логика бота

1. Пользователь отправляет серийный номер текстом
2. Бот отвечает: серийник + кнопки **[📎 В чат]** **[🖨 На печать]**
3. **В чат** → callback `send_to_chat` → генерирует QR + barcode в thread pool → отправляет 2 PNG
4. **На печать** → WebAppInfo → открывает webapp с `?data=SERIAL`

## Технические детали

- Webhook если `PORT` + `WEBHOOK_URL` заданы, иначе polling (локально)
- Генерация через `loop.run_in_executor` — не блокирует event loop
- QR и barcode генерируются параллельно через `asyncio.gather`
- `context.user_data['serial']` — последний серийник для callback
- `requirements.txt` должен содержать `python-telegram-bot[webhooks]` (не просто `python-telegram-bot`)

## Webapp (webapp/index.html)

- Кнопки типа: **QR код** / **Штрих-код** — переключают отображение, сохраняются в localStorage
- Кнопки размера: **100×100 мм** / **50×40 мм** — задают `@page { size: Wmm Hmm; margin: 0 }`
- JS вставляет стиль перед печатью → нет колонтитулов, автомасштаб под лист

## Railway

- `Procfile`: `web: python bot.py`
- `.python-version`: `3.11`
- Переменные: `BOT_TOKEN`, `WEBAPP_URL`, `WEBHOOK_URL` (PORT — автоматически)

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
