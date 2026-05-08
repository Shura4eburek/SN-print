# generator.py

Генерация PNG-изображений QR-кода и штрихкода (Code128).

## Функции

### `generate_qr(data: str) -> io.BytesIO`
- Создаёт QR с `ERROR_CORRECT_M`, box_size=10, border=2
- Ресайз до 900×900 px (LANCZOS)
- Добавляет серийник текстом снизу через `_add_serial()`
- Сохраняет PNG с dpi=(300, 300)

### `generate_barcode(data: str) -> io.BytesIO`
- Code128 через `python-barcode`, `write_text=False`, dpi=300
- Ресайз до ширины 900px с сохранением пропорций
- Добавляет серийник текстом снизу через `_add_serial()`
- Сохраняет PNG с dpi=(300, 300)

### `_add_serial(img, text) -> Image`
- Вычисляет размер шрифта: `max(28, width // 13)`
- Переносит длинный текст через `textwrap.wrap`
- Подклеивает белую полосу снизу с центрированным текстом

### `_get_font(size)`
Пробует шрифты по порядку: `cour.ttf`, `courbd.ttf`, `DejaVuSansMono.ttf`, `arial.ttf`. Fallback — `ImageFont.load_default()`.

## Использование в bot.py

Вызывается через `loop.run_in_executor(None, generate_qr, serial)` — не блокирует event loop.
QR и barcode генерируются параллельно через `asyncio.gather`.
