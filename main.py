"""FastAPI app with Telegram webhook endpoint."""

import logging
import os

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from telegram import Update

from bot import build_application
from logger import close_pool

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")  # e.g. https://your-app.railway.app
WEBHOOK_PATH = "/webhook"

# Build the Telegram application once at module level so it is reused
telegram_app = build_application(TELEGRAM_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting up...")
    await telegram_app.initialize()

    if WEBHOOK_URL:
        full_webhook = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        await telegram_app.bot.set_webhook(url=full_webhook)
        logger.info("Webhook registered: %s", full_webhook)
    else:
        logger.warning(
            "WEBHOOK_URL is not set — Telegram will not deliver messages. "
            "Add WEBHOOK_URL=https://<your-railway-domain> in Railway Variables."
        )

    yield
    logger.info("Shutting down...")
    await telegram_app.bot.delete_webhook()
    await telegram_app.shutdown()
    await close_pool()


app = FastAPI(title="Elliott Wave Content Generator", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "ok"}


@app.post(WEBHOOK_PATH)
async def webhook(request: Request) -> Response:
    """Receive Telegram webhook updates."""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(content="ok", status_code=200)
