"""Telegram bot service - send messages, receive commands and replies."""

import asyncio
import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

logger = logging.getLogger(__name__)

# Callback for when a message is received from the user
_message_callback: Callable[[str], Coroutine] | None = None
# Queue for pending agent decisions (approve/reject/etc.)
_decision_queue: asyncio.Queue = asyncio.Queue()
_bot_app = None


def set_message_callback(cb: Callable[[str], Coroutine]) -> None:
    global _message_callback
    _message_callback = cb


async def send_message(text: str, chat_id: str | None = None) -> bool:
    """Send a plain text message to the configured chat."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping Telegram message.")
        return False
    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        logger.warning("TELEGRAM_CHAT_ID not set, skipping Telegram message.")
        return False
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        # Telegram max message length is 4096
        for chunk in _split_text(text, 4000):
            await bot.send_message(chat_id=target, text=chunk, parse_mode="Markdown")
        return True
    except TelegramError as exc:
        logger.error(f"Telegram send error: {exc}")
        return False


async def send_post_for_review(post_content: str, context: str = "") -> None:
    """Send a generated post to the user for approval."""
    header = "📝 *New LinkedIn Post Draft*\n\n"
    if context:
        header += f"_{context}_\n\n"
    body = f"{header}{post_content}\n\n"
    body += (
        "---\nReply with:\n"
        "✅ `approve` - Post is good\n"
        "❌ `reject` - Skip this post\n"
        "✏️ `improve: <feedback>` - Request changes\n"
        "🔁 `regenerate` - Generate a new version"
    )
    await send_message(body)


async def get_user_decision(timeout: int = 86400) -> dict[str, Any]:
    """Wait for the user's decision on a post (with timeout in seconds)."""
    try:
        return await asyncio.wait_for(_decision_queue.get(), timeout=float(timeout))
    except asyncio.TimeoutError:
        return {"action": "timeout"}


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.message.reply_text(
        f"👋 LinkedIn Agent is running!\nYour chat ID is: `{chat_id}`\n\n"
        "Commands:\n"
        "/status - Agent status\n"
        "/todo - Show pending tasks\n"
        "/post <topic> - Draft a post on a custom topic\n"
        "/repos - Show tracked repos\n"
        "/skip - Skip current task",
        parse_mode="Markdown",
    )


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id) if update.effective_chat else ""

    # Only process messages from the configured chat
    if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
        return

    lower = text.lower()
    if lower == "approve":
        await _decision_queue.put({"action": "approve"})
    elif lower == "reject":
        await _decision_queue.put({"action": "reject"})
    elif lower == "regenerate":
        await _decision_queue.put({"action": "regenerate"})
    elif lower.startswith("improve:"):
        feedback = text[len("improve:"):].strip()
        await _decision_queue.put({"action": "improve", "feedback": feedback})
    elif _message_callback:
        await _message_callback(text)
    else:
        await _decision_queue.put({"action": "message", "text": text})


async def _handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        await _message_callback("/status")


async def _handle_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        await _message_callback("/todo")


async def _handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    topic = " ".join(args) if args else ""
    if _message_callback:
        await _message_callback(f"/post {topic}")


async def _handle_repos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        await _message_callback("/repos")


async def _handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _decision_queue.put({"action": "reject"})
    await update.message.reply_text("⏭️ Skipped current task.")


def _split_text(text: str, max_len: int) -> list[str]:
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


async def start_bot(message_callback: Callable[[str], Coroutine] | None = None) -> None:
    """Start the Telegram bot in polling mode (runs in background)."""
    global _bot_app
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot disabled.")
        return

    if message_callback:
        set_message_callback(message_callback)

    _bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    _bot_app.add_handler(CommandHandler("start", _handle_start))
    _bot_app.add_handler(CommandHandler("status", _handle_status))
    _bot_app.add_handler(CommandHandler("todo", _handle_todo))
    _bot_app.add_handler(CommandHandler("post", _handle_post))
    _bot_app.add_handler(CommandHandler("repos", _handle_repos))
    _bot_app.add_handler(CommandHandler("skip", _handle_skip))
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    await _bot_app.initialize()
    await _bot_app.start()
    await _bot_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started.")


async def stop_bot() -> None:
    global _bot_app
    if _bot_app:
        await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()
        _bot_app = None
