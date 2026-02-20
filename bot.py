import asyncio
import os
import re
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from generator import generate_qr, generate_barcode

load_dotenv()
BOT_TOKEN   = os.getenv("BOT_TOKEN")
WEBAPP_URL  = os.getenv("WEBAPP_URL", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT        = int(os.getenv("PORT", 0))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Отправь серийный номер — появятся кнопки:\n"
        "• В чат — получишь QR и штрихкод файлами\n"
        "• На печать — откроется Mini App"
    )


def clean_serial(text: str) -> str:
    """Убрать служебные символы, которые добавляют некоторые сканеры (напр. '[')."""
    return re.sub(r'^[^\w\-]+', '', text.strip())


async def handle_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    serial = clean_serial(update.message.text)

    # Сохраняем серийник для callback
    context.user_data["serial"] = serial

    buttons = [[InlineKeyboardButton("📎 В чат", callback_data="send_to_chat")]]
    if WEBAPP_URL:
        qs = urlencode({"data": serial})
        buttons[0].append(
            InlineKeyboardButton(
                "🖨 На печать",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?{qs}"),
            )
        )

    await update.message.reply_text(
        serial,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def callback_send_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    serial = context.user_data.get("serial")
    if not serial:
        await query.answer("Серийный номер не найден, отправь его снова", show_alert=True)
        return

    loop = asyncio.get_event_loop()
    try:
        qr_buf, bar_buf = await asyncio.gather(
            loop.run_in_executor(None, generate_qr, serial),
            loop.run_in_executor(None, generate_barcode, serial),
        )
    except Exception as e:
        logger.error("Generation error: %s", e)
        await query.message.reply_text(f"Ошибка генерации: {e}")
        return

    await query.message.reply_document(document=qr_buf, filename=f"{serial}_qr.png")
    await query.message.reply_document(document=bar_buf, filename=f"{serial}_barcode.png")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Создайте файл .env с BOT_TOKEN=...")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_serial))
    app.add_handler(CallbackQueryHandler(callback_send_to_chat, pattern="^send_to_chat$"))

    if PORT and WEBHOOK_URL:
        logger.info("Запуск в режиме webhook на порту %d", PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{BOT_TOKEN}",
        )
    else:
        logger.info("Запуск в режиме polling")
        app.run_polling()


if __name__ == "__main__":
    main()
