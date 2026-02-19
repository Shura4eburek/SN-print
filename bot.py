import os
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Отправь серийный номер — получишь QR-код и штрих-код.\n"
        "Кнопка «Открыть для печати» откроет Mini App."
    )


async def handle_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    serial = update.message.text.strip()

    try:
        qr_buf = generate_qr(serial)
        bar_buf = generate_barcode(serial)
    except Exception as e:
        logger.error("Generation error: %s", e)
        await update.message.reply_text(f"Ошибка генерации: {e}")
        return

    # Отправляем оба файла без подписи
    await update.message.reply_document(document=qr_buf, filename=f"{serial}_qr.png")
    await update.message.reply_document(document=bar_buf, filename=f"{serial}_barcode.png")

    # Кнопка для печати через Mini App
    if WEBAPP_URL:
        qs = urlencode({"data": serial})
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Открыть для печати",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?{qs}")
            )
        ]])
        await update.message.reply_text("Печать:", reply_markup=reply_markup)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Создайте файл .env с BOT_TOKEN=...")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_serial))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
