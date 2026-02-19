import os
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from generator import generate_qr, generate_barcode

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# { user_id: {"type": "qr"|"barcode", "size": "100x100"|"50x40"} }
user_settings: dict[int, dict] = {}

SIZE_MAP = {
    "100x100": (100, 100),
    "50x40": (50, 40),
}  # значения в пикселях

DEFAULT_SETTINGS = {"type": "qr", "size": "100x100"}


def get_settings(user_id: int) -> dict:
    return user_settings.setdefault(user_id, DEFAULT_SETTINGS.copy())


def build_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    qr_mark = "✅ " if settings["type"] == "qr" else ""
    bar_mark = "✅ " if settings["type"] == "barcode" else ""
    s100_mark = "✅ " if settings["size"] == "100x100" else ""
    s50_mark = "✅ " if settings["size"] == "50x40" else ""

    keyboard = [
        [
            InlineKeyboardButton(f"{qr_mark}QR код", callback_data="type:qr"),
            InlineKeyboardButton(f"{bar_mark}Штрих-код", callback_data="type:barcode"),
        ],
        [
            InlineKeyboardButton(f"{s100_mark}100×100 px", callback_data="size:100x100"),
            InlineKeyboardButton(f"{s50_mark}50×40 px", callback_data="size:50x40"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я генерирую QR-коды и штрих-коды.\n\n"
        "Отправь мне серийный номер — получишь PNG-файл.\n"
        "Используй /settings, чтобы выбрать тип и размер кода."
    )


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = get_settings(user_id)
    await update.message.reply_text(
        "Настройки:",
        reply_markup=build_settings_keyboard(settings),
    )


async def callback_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    settings = get_settings(user_id)

    key, value = query.data.split(":", 1)
    settings[key] = value

    await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(settings))


async def handle_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = get_settings(user_id)
    serial = update.message.text.strip()

    size_px = SIZE_MAP[settings["size"]]
    code_type = settings["type"]

    try:
        if code_type == "qr":
            buf = generate_qr(serial, size_px)
        else:
            buf = generate_barcode(serial, size_px)
    except Exception as e:
        logger.error("Generation error: %s", e)
        await update.message.reply_text(f"Ошибка генерации: {e}")
        return

    size_label = settings["size"].replace("x", "×")
    type_label = "QR-код" if code_type == "qr" else "Штрих-код"
    caption = f"{type_label} · {serial} · {size_label} px"

    reply_markup = None
    if WEBAPP_URL:
        qs = urlencode({"type": code_type, "data": serial})
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Открыть для печати",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?{qs}")
            )
        ]])

    await update.message.reply_document(
        document=buf,
        filename=f"{serial}.png",
        caption=caption,
        reply_markup=reply_markup,
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Создайте файл .env с BOT_TOKEN=...")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(callback_settings))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_serial))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
