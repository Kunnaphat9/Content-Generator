"""Telegram bot handlers."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from generator import generate_content

logger = logging.getLogger(__name__)

TRIGGER_PHRASE = "ขอบทความ"


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "สวัสดีครับ! พิมพ์ *ขอบทความ* เพื่อรับ Content Idea และ Draft Outline "
        "สำหรับบทความ Elliott Wave ครับ",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    text = update.message.text or ""

    if TRIGGER_PHRASE not in text:
        return

    # Acknowledge the request
    processing_msg = await update.message.reply_text(
        "กำลังสร้างบทความอยู่นะครับ รอสักครู่... ⏳",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        content = await generate_content()
        await processing_msg.delete()
        await update.message.reply_text(
            content,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.exception("Content generation failed: %s", exc)
        await processing_msg.edit_text(
            "ขอโทษครับ เกิดข้อผิดพลาดในการสร้างบทความ กรุณาลองใหม่อีกครั้งครับ ❌"
        )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Update %s caused error: %s", update, context.error)


def build_application(token: str) -> Application:
    """Build and configure the Telegram Application."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_error_handler(handle_error)
    return app
