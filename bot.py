"""Telegram bot handlers."""

import logging
import httpx

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from generator import generate_full_article, generate_outlines
from knowledge import fetch_style_guide

logger = logging.getLogger(__name__)

TRIGGER_PHRASE = "ขอบทความ"

# In-memory state: chat_id → pending outline selection data
_pending: dict[int, dict] = {}

OUTLINE_LABELS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "สวัสดีครับ! พิมพ์ *ขอบทความ* เพื่อรับ 5 แนวทางบทความ Elliott Wave "
        "แล้วเลือกแนวทางที่ชอบเพื่อให้แอดเขียนบทความเต็มๆ ครับ",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    text = update.message.text or ""
    chat_id = update.message.chat_id
    logger.info("Message received: %r (chat_id=%s)", text, chat_id)

    if TRIGGER_PHRASE not in text:
        logger.info("Trigger phrase not found — ignoring")
        return

    logger.info("Trigger matched — generating outlines")

    try:
        processing_msg = await update.message.reply_text(
            "กำลังสร้างแนวทางบทความอยู่นะครับ รอสักครู่... ⏳",
        )
    except Exception as exc:
        logger.exception("Failed to send processing message: %s", exc)
        return

    try:
        result = await generate_outlines()
        outlines = result["outlines"]
        chunk_id = result["chunk_id"]
        dimension = result["dimension"]
        chunk_data = result["chunk_data"]

        # Build display message listing all 5 outlines
        lines = [f"📋 *แนวทางบทความ* | Chunk: `{chunk_id}` | `{dimension}`\n{'─' * 35}\n"]
        for i, outline in enumerate(outlines):
            if outline:
                lines.append(f"{OUTLINE_LABELS[i]}\n{outline}\n")

        lines.append("\nเลือกแนวทางที่ชอบได้เลยครับ 👇")
        display_text = "\n".join(lines)

        # Store state so callback knows which outlines belong to this chat
        _pending[chat_id] = {
            "outlines": outlines,
            "chunk_data": chunk_data,
            "dimension": dimension,
        }

        # Build inline keyboard — only show buttons for non-empty outlines
        keyboard = [
            [
                InlineKeyboardButton(OUTLINE_LABELS[i], callback_data=f"outline:{i}")
                for i in range(len(outlines))
                if outlines[i]
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.delete()

        # Telegram message limit is 4096 chars
        if len(display_text) <= 4096:
            await update.message.reply_text(
                display_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
        else:
            # Send outlines without markdown if too long to avoid parse errors
            await update.message.reply_text(
                display_text[:4090] + "…",
                reply_markup=reply_markup,
            )

    except httpx.HTTPStatusError as exc:
        logger.exception("GitHub fetch failed: %s", exc)
        await processing_msg.edit_text(
            f"❌ ดึงไฟล์จาก GitHub ไม่ได้ครับ ({exc.response.status_code})\n"
            f"URL: {exc.request.url}\n\n"
            "กรุณาตรวจสอบว่า GITHUB_RAW_BASE_URL ชี้ไปที่ branch ที่ถูกต้องครับ"
        )
    except httpx.RequestError as exc:
        logger.exception("GitHub network error: %s", exc)
        await processing_msg.edit_text(
            f"❌ เชื่อมต่อ GitHub ไม่ได้ครับ\nError: {type(exc).__name__}\n\nกรุณาลองใหม่อีกครั้งครับ"
        )
    except RuntimeError as exc:
        logger.exception("Runtime error: %s", exc)
        await processing_msg.edit_text(f"❌ เกิดข้อผิดพลาดครับ\n\n{exc}")
    except Exception as exc:
        logger.exception("Outline generation failed: %s", exc)
        await processing_msg.edit_text(
            f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิดครับ\n\n[{type(exc).__name__}] {exc}"
        )


async def handle_outline_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button press — generate full article for selected outline."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data  # e.g. "outline:2"

    if not data.startswith("outline:"):
        return

    try:
        index = int(data.split(":")[1])
    except (ValueError, IndexError):
        await query.message.reply_text("❌ ข้อมูล callback ไม่ถูกต้องครับ")
        return

    state = _pending.get(chat_id)
    if not state:
        await query.message.reply_text(
            "❌ ไม่พบข้อมูล outline ครับ ลองพิมพ์ *ขอบทความ* ใหม่อีกครั้งนะครับ",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    outlines = state["outlines"]
    if index >= len(outlines) or not outlines[index]:
        await query.message.reply_text("❌ ไม่พบแนวทางที่เลือกครับ")
        return

    selected_outline = outlines[index]
    chunk_data = state["chunk_data"]
    dimension = state["dimension"]

    # Remove inline keyboard from the outlines message
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass  # non-critical

    processing_msg = await query.message.reply_text(
        f"กำลังเขียนบทความแนวทาง {OUTLINE_LABELS[index]} อยู่นะครับ รอสักครู่... ✍️",
    )

    try:
        style_data = await fetch_style_guide()
        article = await generate_full_article(selected_outline, chunk_data, dimension, style_data)

        await processing_msg.delete()

        if len(article) <= 4096:
            await query.message.reply_text(article)
        else:
            # Split at a paragraph boundary near 4000 chars
            split_at = article.rfind("\n\n", 0, 4000)
            if split_at == -1:
                split_at = 4000
            await query.message.reply_text(article[:split_at])
            await query.message.reply_text(article[split_at:].lstrip())

        # Clear pending state after successful generation
        _pending.pop(chat_id, None)

    except httpx.HTTPStatusError as exc:
        logger.exception("GitHub fetch failed during article gen: %s", exc)
        await processing_msg.edit_text(
            f"❌ ดึง style guide ไม่ได้ครับ ({exc.response.status_code})"
        )
    except Exception as exc:
        logger.exception("Article generation failed: %s", exc)
        await processing_msg.edit_text(
            f"❌ เขียนบทความไม่สำเร็จครับ\n\n[{type(exc).__name__}] {exc}"
        )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Update %s caused error: %s", update, context.error)


def build_application(token: str) -> Application:
    """Build and configure the Telegram Application."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_outline_selection, pattern=r"^outline:\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)
    return app
