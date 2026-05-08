# metricon_client.py

Standalone-клиент для системы мониторинга Metricon. Версия: `1.1.0`.
Dashboard: https://web-production-37313.up.railway.app

**Не изменять без явной просьбы.** Файл может автообновляться с сервера.

## Инициализация

```python
metricon = MetriconClient(
    server_url=METRICON_URL,
    api_key=METRICON_API_KEY,
    bot_name="SN-print",
)
metricon.start()  # запускает heartbeat и flush в daemon-тредах
```

`metricon.start()` вызывать при старте бота. `metricon.stop()` — при завершении (flush последнего батча).

## API методов

| Метод | Назначение |
|---|---|
| `track_request(command, response_time_ms, user_id, success)` | Лог запроса в батч |
| `track_error(exc, command)` | Fire-and-forget событие ошибки |
| `track_metric(key, value)` | Fire-and-forget кастомная метрика |
| `@metricon.track` | Декоратор — автоматически пишет request + error (sync и async) |

**Порядок параметров `track_request`**: `command`, `response_time_ms`, `user_id`, `success` (не путать с user_id первым).

## Внутренняя архитектура

- Все HTTP-запросы — в daemon-тредах, никогда не блокируют event loop
- Батч запросов флашится каждые 5 сек или при достижении 50 записей
- Heartbeat отправляется каждые 30 сек с CPU, RAM, uptime, версией клиента
- При ответе сервера `update: true` — автоскачивает новую версию себя и рестартует процесс (`os.execv`)

## HTTP endpoints

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/v1/bots/heartbeat/` | Пульс |
| POST | `/api/v1/metrics/request/batch/` | Батч логов запросов |
| POST | `/api/v1/metrics/error/` | Событие ошибки |
| POST | `/api/v1/metrics/custom/` | Кастомная метрика |

Аутентификация: заголовок `X-API-Key`.

## Первичная регистрация

```python
client = MetriconClient.register(server_url="...", name="my-bot")
print(client.api_key)  # сохранить в .env
```
