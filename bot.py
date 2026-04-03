"""Telegram bot handlers."""

import logging
import httpx

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from generator import generate_full_article, generate_outlines
from knowledge import fetch_chapter_list, fetch_style_guide

logger = logging.getLogger(__name__)

TRIGGER_PHRASE = "ขอบทความ"

# In-memory state: chat_id → pending data
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
    """Handle incoming text messages — show chapter selection keyboard."""
    text = update.message.text or ""
    chat_id = update.message.chat_id
    logger.info("Message received: %r (chat_id=%s)", text, chat_id)

    if TRIGGER_PHRASE not in text:
        logger.info("Trigger phrase not found — ignoring")
        return

    logger.info("Trigger matched — fetching chapter list")

    try:
        chapters = await fetch_chapter_list()
    except Exception as exc:
        logger.exception("Failed to fetch chapter list: %s", exc)
        await update.message.reply_text("❌ ดึงรายการบทไม่ได้ครับ ลองใหม่อีกครั้งนะครับ")
        return

    if not chapters:
        await update.message.reply_text("❌ ไม่พบบทเรียนในฐานข้อมูลครับ")
        return

    # Build display message
    lines = ["📚 *เลือกบทที่ต้องการได้เลยครับ*\n"]
    for ch in chapters:
        lines.append(f"• *บทที่ {ch['chapter']}* — {ch['title']} ({ch['chunk_count']} chunks)")
    display_text = "\n".join(lines)

    # Build keyboard — one button per chapter
    keyboard = [[
        InlineKeyboardButton(f"บทที่ {ch['chapter']}", callback_data=f"chapter:{ch['id']}")
        for ch in chapters
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        display_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def handle_chapter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chapter button press — generate 5 outlines for the selected chapter."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    chapter_id = query.data.split(":", 1)[1]  # e.g. "chapter1"

    # Remove chapter selection keyboard
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    processing_msg = await query.message.reply_text(
        "กำลังสร้างแนวทางบทความอยู่นะครับ รอสักครู่... ⏳",
    )

    try:
        result = await generate_outlines(chapter_id)
        outlines = result["outlines"]
        chunk_id = result["chunk_id"]
        dimension = result["dimension"]
        chunk_data = result["chunk_data"]

        lines = [f"📋 *แนวทางบทความ* | Chunk: `{chunk_id}` | `{dimension}`\n{'─' * 35}\n"]
        for i, outline in enumerate(outlines):
            if outline:
                lines.append(f"{OUTLINE_LABELS[i]}\n{outline}\n")
        lines.append("\nเลือกแนวทางที่ชอบได้เลยครับ 👇")
        display_text = "\n".join(lines)

        _pending[chat_id] = {
            "outlines": outlines,
            "chunk_data": chunk_data,
            "dimension": dimension,
        }

        keyboard = [[
            InlineKeyboardButton(OUTLINE_LABELS[i], callback_data=f"outline:{i}")
            for i in range(len(outlines))
            if outlines[i]
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.delete()

        if len(display_text) <= 4096:
            await query.message.reply_text(
                display_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
        else:
            await query.message.reply_text(
                display_text[:4090] + "…",
                reply_markup=reply_markup,
            )

    except httpx.HTTPStatusError as exc:
        logger.exception("GitHub fetch failed: %s", exc)
        await processing_msg.edit_text(
            f"❌ ดึงไฟล์จาก GitHub ไม่ได้ครับ ({exc.response.status_code})\n"
            f"URL: {exc.request.url}"
        )
    except httpx.RequestError as exc:
        logger.exception("GitHub network error: %s", exc)
        await processing_msg.edit_text(
            f"❌ เชื่อมต่อ GitHub ไม่ได้ครับ\nError: {type(exc).__name__}"
        )
    except Exception as exc:
        logger.exception("Outline generation failed: %s", exc)
        await processing_msg.edit_text(
            f"❌ เกิดข้อผิดพลาดครับ\n\n[{type(exc).__name__}] {exc}"
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

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

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
            split_at = article.rfind("\n\n", 0, 4000)
            if split_at == -1:
                split_at = 4000
            await query.message.reply_text(article[:split_at])
            await query.message.reply_text(article[split_at:].lstrip())

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
    app.add_handler(CallbackQueryHandler(handle_chapter_selection, pattern=r"^chapter:.+$"))
    app.add_handler(CallbackQueryHandler(handle_outline_selection, pattern=r"^outline:\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)
    return app
