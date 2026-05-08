# bot.py

Точка входа. Инициализирует бота, регистрирует хендлеры, запускает polling или webhook.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота (обязателен) |
| `WEBAPP_URL` | Базовый URL GitHub Pages webapp |
| `WEBHOOK_URL` | Railway URL для webhook-режима |
| `PORT` | Порт (Railway выставляет автоматически) |
| `METRICON_API_KEY` | Ключ для Metricon мониторинга |
| `METRICON_URL` | URL Metricon-сервера (по умолчанию Railway) |

## Хендлеры

| Хендлер | Триггер | Действие |
|---|---|---|
| `cmd_start` | `/start` | Приветствие + ReplyKeyboard с кнопкой «Створити утиль» |
| `handle_serial` | любой текст | `clean_serial()` → сохранить в `context.user_data['serial']` → кнопки В чат / На печать |
| `callback_send_to_chat` | callback `send_to_chat` | `asyncio.gather` двух `run_in_executor` → 2 PNG в чат |

## Логика запуска

- Если заданы `PORT` и `WEBHOOK_URL` → `app.run_webhook(listen="0.0.0.0", ...)`
- Иначе → `app.run_polling()` (локальная разработка)

## clean_serial

```python
re.sub(r'^[^\w\-]+', '', text.strip())
```
Убирает ведущие нечитаемые символы, которые добавляют некоторые сканеры (напр. `[`).

## ReplyKeyboard

`make_reply_keyboard()` возвращает постоянную кнопку над полем ввода, открывающую `util.html` через WebAppInfo. Возвращает `None`, если `WEBAPP_URL` не задан.

## Metricon в хендлерах

Вызовы синхронные, без await:
```python
metricon.track_request(command, response_time_ms, user_id, success)
metricon.track_error(exc, command)
```
`metricon` может быть `None` — всегда проверять `if metricon:`.
