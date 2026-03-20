"""Telegram bot service - send messages, receive commands and replies."""

import asyncio
import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Bot, Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

import storage

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Proxy URL for regions where Telegram is blocked (e.g. socks5://user:pass@host:port
# or https://user:pass@host:port).  Can also be set via the standard HTTPS_PROXY env var.
TELEGRAM_PROXY = (
    os.getenv("TELEGRAM_PROXY", "")
    or os.getenv("HTTPS_PROXY", "")
    or os.getenv("https_proxy", "")
)
TELEGRAM_MESSAGE_CHUNK_SIZE = 4000
# How often (seconds) the background task checks for pending messages to flush
PENDING_FLUSH_INTERVAL = 60
# How long (seconds) to wait before retrying a failed bot startup
BOT_RETRY_INTERVAL = PENDING_FLUSH_INTERVAL

logger = logging.getLogger(__name__)

# Callback for when a message is received from the user
_message_callback: Callable[[str], Coroutine] | None = None
# Queue for pending agent decisions (approve/reject/etc.)
_decision_queue: asyncio.Queue = asyncio.Queue()
_bot_app = None
# In-memory pending messages list (also persisted via storage)
_pending_messages: list[str] = []
# Background tasks
_pending_flush_task: asyncio.Task | None = None
_bot_start_task: asyncio.Task | None = None


def set_message_callback(cb: Callable[[str], Coroutine]) -> None:
    global _message_callback
    _message_callback = cb


def _make_request() -> HTTPXRequest | None:
    """Build an HTTPXRequest with proxy configured, or None for default."""
    if TELEGRAM_PROXY:
        logger.info("Telegram: using proxy %s", TELEGRAM_PROXY)
        return HTTPXRequest(proxy=TELEGRAM_PROXY)
    return None


async def send_message(text: str, chat_id: str | None = None) -> bool:
    """Send a plain text message to the configured chat.

    If Telegram is unreachable, the message is queued and will be sent once
    the connection is restored.  Markdown parse errors are handled by falling
    back to plain text for the affected chunk so that a formatting mistake in
    generated content never causes the message to be queued for infinite retry.
    Only the unsent portion is queued on a transient network failure.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping Telegram message.")
        return False
    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        logger.warning("TELEGRAM_CHAT_ID not set, skipping Telegram message.")
        return False

    try:
        req = _make_request()
        bot = Bot(token=TELEGRAM_BOT_TOKEN, request=req) if req else Bot(token=TELEGRAM_BOT_TOKEN)
    except Exception as exc:
        logger.error("Failed to create Telegram bot: %s — queuing message for retry.", exc)
        _queue_pending_message(text)
        return False

    chunks = _split_text(text, TELEGRAM_MESSAGE_CHUNK_SIZE)
    for i, chunk in enumerate(chunks):
        remainder = "\n".join(chunks[i:])
        try:
            await bot.send_message(chat_id=target, text=chunk, parse_mode="Markdown")
        except BadRequest as md_exc:
            # Markdown parsing failed — log and retry this chunk as plain text.
            logger.warning("Markdown parse error for chunk %d/%d: %s — retrying as plain text.", i + 1, len(chunks), md_exc)
            try:
                await bot.send_message(chat_id=target, text=chunk)
            except TelegramError as exc:
                logger.error(
                    "Telegram send error (plain text fallback): %s — queuing remainder for retry.", exc
                )
                _queue_pending_message(remainder)
                return False
            except Exception as exc:
                logger.error(
                    "Unexpected error (plain text fallback): %s — queuing remainder for retry.", exc
                )
                _queue_pending_message(remainder)
                return False
        except TelegramError as exc:
            logger.error("Telegram send error: %s — queuing remainder for retry.", exc)
            _queue_pending_message(remainder)
            return False
        except Exception as exc:
            logger.error(
                "Unexpected error sending Telegram message: %s — queuing remainder for retry.", exc
            )
            _queue_pending_message(remainder)
            return False
    return True


def _queue_pending_message(text: str) -> None:
    """Add a message to the in-memory and persistent pending queue."""
    _pending_messages.append(text)
    try:
        storage.add_pending_message(text)
    except Exception as exc:
        logger.warning("Could not persist pending message: %s", exc)


async def flush_pending_messages() -> int:
    """Try to send all queued pending messages.  Returns the number successfully sent.

    A snapshot of the queue is taken before flushing so that any messages
    enqueued concurrently (e.g. from the main agent loop during an ``await``)
    are not accidentally discarded when the snapshot's remainder is written back.
    """
    global _pending_messages
    if not _pending_messages:
        return 0

    # Snapshot the current queue and reset the live list so that messages
    # produced during the flush accumulate in the fresh list.
    snapshot = _pending_messages
    _pending_messages = []

    sent_count = 0
    failed_idx: int | None = None
    for i, msg in enumerate(snapshot):
        ok = await _send_direct(msg)
        if ok:
            sent_count += 1
        else:
            # Telegram still down — stop attempting; carry over this and all remaining.
            failed_idx = i
            break

    unsent_from_snapshot = snapshot[failed_idx:] if failed_idx is not None else []
    # Combine unsent snapshot messages with any new messages added during the flush.
    _pending_messages = unsent_from_snapshot + _pending_messages
    try:
        storage.save_pending_messages(_pending_messages)
    except Exception as exc:
        logger.warning("Could not update persisted pending messages: %s", exc)

    if sent_count:
        logger.info("Flushed %d pending Telegram message(s).", sent_count)
    return sent_count


async def _send_direct(text: str, chat_id: str | None = None) -> bool:
    """Low-level send that does NOT queue on failure (used for flush retries).

    Falls back to plain text if Markdown parsing fails, so that messages with
    malformed Markdown are not silently dropped on every flush attempt.
    """
    if not TELEGRAM_BOT_TOKEN:
        return False
    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        return False
    try:
        req = _make_request()
        bot = Bot(token=TELEGRAM_BOT_TOKEN, request=req) if req else Bot(token=TELEGRAM_BOT_TOKEN)
        for chunk in _split_text(text, TELEGRAM_MESSAGE_CHUNK_SIZE):
            try:
                await bot.send_message(chat_id=target, text=chunk, parse_mode="Markdown")
            except BadRequest as md_exc:
                # Markdown parsing failed — log and retry as plain text.
                logger.debug("Markdown parse error during flush: %s — retrying as plain text.", md_exc)
                await bot.send_message(chat_id=target, text=chunk)
        return True
    except Exception as exc:
        logger.debug("Flush send attempt failed: %s", exc)
        return False


async def _pending_flush_loop() -> None:
    """Background task: periodically flush pending messages."""
    while True:
        try:
            await asyncio.sleep(PENDING_FLUSH_INTERVAL)
            await flush_pending_messages()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Pending flush loop error: %s", exc)


async def send_post_for_review(post_content: str, context: str = "") -> None:
    """Send a generated post to the user for approval.

    Any stale decisions left in the queue from a previous session are discarded
    before the new review message is sent, so that an old queued "reject" cannot
    silently skip a brand-new post.
    """
    # Drain stale decisions that were queued while no review was active.
    drained = 0
    while not _decision_queue.empty():
        try:
            _decision_queue.get_nowait()
            drained += 1
        except asyncio.QueueEmpty:
            break
    if drained:
        logger.warning(
            "Discarded %d stale decision(s) from queue before new post review.", drained
        )

    header = "📝 *New LinkedIn Post Draft*\n\n"
    if context:
        header += f"_{context}_\n\n"
    body = f"{header}{post_content}\n\n"
    body += (
        "---\nReply with:\n"
        "✅ `approve` - Post is good\n"
        "❌ `reject` - Skip this post\n"
        "✏️ `improve: <feedback>` - Request changes\n"
        "🔁 `regenerate` - Generate a new version\n\n"
        "💡 _Tip: You can also attach an image/photo to include with this post on LinkedIn._"
    )
    await send_message(body)


async def get_user_decision(timeout: int = 86400) -> dict[str, Any]:
    """Wait for the user's decision on a post (with timeout in seconds)."""
    try:
        return await asyncio.wait_for(_decision_queue.get(), timeout=float(timeout))
    except asyncio.TimeoutError:
        return {"action": "timeout"}


def _schedule_callback(text: str) -> None:
    """Fire the message callback as a non-blocking background task.

    PTB processes updates sequentially by default (concurrent_updates=False).
    If we directly ``await _message_callback(text)`` from a handler, the handler
    coroutine stays alive until the callback returns — which can take up to 24 h
    when the callback triggers a post-review loop that waits for user input.
    While that handler is alive PTB cannot dispatch any new updates, so the
    user's subsequent "reject"/"approve" messages are never processed, causing
    a permanent deadlock where the bot appears completely unresponsive.

    Scheduling the callback as a separate asyncio Task lets every PTB handler
    return immediately, keeping PTB's update loop free to process incoming
    messages (including the decision keywords needed to unblock the callback).
    """
    if not _message_callback:
        return

    async def _run() -> None:
        try:
            await _message_callback(text)
        except Exception as exc:
            logger.error("Message callback error for %r: %s", text[:80], exc)

    asyncio.create_task(_run())


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.message.reply_text(
        f"👋 LinkedIn Agent is running!\nYour chat ID is: `{chat_id}`\n\n"
        "Commands:\n"
        "/commands - Show all available commands\n"
        "/status - Agent status\n"
        "/todo - Show pending tasks\n"
        "/todo add <task> - Add a new task\n"
        "/todo done <id> - Mark a task as done\n"
        "/post <topic> - Draft a post on a topic\n"
        "/post repo:<name> - Draft a post for a specific repo\n"
        "/postrepo <name> - Draft a post for a specific repo\n"
        "/postactivity - Draft a post from latest GitHub activity\n"
        "/postsource - Draft a post from latest tech news\n"
        "/repos - Show tracked repos\n"
        "/memory - Show the post memory log\n"
        "/readme <repo> - Show a repo's README\n"
        "/pending - Show pending draft posts\n"
        "/skip - Skip current task\n\n"
        "💬 You can also just chat naturally!",
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
    elif lower in ("yes", "y"):
        await _decision_queue.put({"action": "yes"})
    elif lower in ("no", "n", "nope", "stop", "enough", "that's enough", "thats enough"):
        await _decision_queue.put({"action": "no"})
    elif _message_callback:
        # Run in a background task so this handler returns immediately and PTB
        # can continue dispatching subsequent updates (e.g. "reject"/"approve").
        _schedule_callback(text)
    else:
        await _decision_queue.put({"action": "message", "text": text})


async def _handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/status")


async def _handle_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    suffix = " " + " ".join(args) if args else ""
    if _message_callback:
        _schedule_callback(f"/todo{suffix}")


async def _handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    topic = " ".join(args) if args else ""
    if _message_callback:
        _schedule_callback(f"/post {topic}")


async def _handle_repos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/repos")


async def _handle_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/memory")


async def _handle_readme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    repo_name = " ".join(args) if args else ""
    if _message_callback:
        _schedule_callback(f"/readme {repo_name}")


async def _handle_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/pending")


async def _handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _decision_queue.put({"action": "reject"})
    await update.message.reply_text("⏭️ Skipped current task.")


async def _handle_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/commands")


async def _handle_post_repo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    repo_name = " ".join(args) if args else ""
    if _message_callback:
        _schedule_callback(f"/postrepo {repo_name}")


async def _handle_post_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/postactivity")


async def _handle_post_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _message_callback:
        _schedule_callback("/postsource")


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


async def _start_bot_inner(message_callback: Callable[[str], Coroutine] | None = None) -> None:
    """Internal helper: initialize and start the bot application."""
    global _bot_app

    # Guard against starting a second bot instance while one is already running
    if _bot_app is not None:
        logger.warning("Telegram bot is already running; skipping duplicate startup.")
        return

    if message_callback:
        set_message_callback(message_callback)

    builder = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN)
    if TELEGRAM_PROXY:
        builder = builder.proxy(TELEGRAM_PROXY).get_updates_proxy(TELEGRAM_PROXY)

    _bot_app = builder.build()
    _bot_app.add_handler(CommandHandler("start", _handle_start))
    _bot_app.add_handler(CommandHandler("status", _handle_status))
    _bot_app.add_handler(CommandHandler("todo", _handle_todo))
    _bot_app.add_handler(CommandHandler("post", _handle_post))
    _bot_app.add_handler(CommandHandler("repos", _handle_repos))
    _bot_app.add_handler(CommandHandler("memory", _handle_memory))
    _bot_app.add_handler(CommandHandler("readme", _handle_readme))
    _bot_app.add_handler(CommandHandler("pending", _handle_pending))
    _bot_app.add_handler(CommandHandler("skip", _handle_skip))
    _bot_app.add_handler(CommandHandler("commands", _handle_commands))
    _bot_app.add_handler(CommandHandler("postrepo", _handle_post_repo))
    _bot_app.add_handler(CommandHandler("postactivity", _handle_post_activity))
    _bot_app.add_handler(CommandHandler("postsource", _handle_post_source))
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    await _bot_app.initialize()
    await _bot_app.start()
    await _bot_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started.")

    # Flush any messages that were queued while the bot was offline
    await flush_pending_messages()


async def _bot_start_with_retry(
    message_callback: Callable[[str], Coroutine] | None = None,
) -> None:
    """Background task: start the bot, retrying every BOT_RETRY_INTERVAL s on failure."""
    while True:
        try:
            await _start_bot_inner(message_callback)
            return  # Successfully started
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.warning(
                "Telegram bot failed to start: %s — retrying in %ds...", exc, BOT_RETRY_INTERVAL
            )
            await asyncio.sleep(BOT_RETRY_INTERVAL)


async def start_bot(message_callback: Callable[[str], Coroutine] | None = None) -> None:
    """Start the Telegram bot in the background (non-blocking).

    The bot startup is launched as an asyncio Task so the agent can continue
    working immediately. If Telegram is unreachable, the task retries every 60 s.
    Pending messages accumulated while offline are flushed once connected.
    """
    global _bot_start_task, _pending_flush_task

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot disabled.")
        return

    if message_callback:
        set_message_callback(message_callback)

    # Load persisted pending messages into in-memory queue and immediately clear storage.
    # Clearing storage here prevents duplicate sends if the server crashes mid-flush:
    # the in-memory list is the single source of truth for this session.
    persisted = storage.load_pending_messages()
    if persisted:
        _pending_messages.extend(persisted)
        storage.clear_pending_messages()
        logger.info("Loaded %d persisted pending message(s) into memory.", len(persisted))

    # Start bot connection in background (non-blocking)
    _bot_start_task = asyncio.create_task(_bot_start_with_retry(message_callback))

    # Start periodic flush loop
    _pending_flush_task = asyncio.create_task(_pending_flush_loop())

    logger.info("Telegram bot startup initiated in background.")


async def stop_bot() -> None:
    global _bot_app, _pending_flush_task, _bot_start_task
    if _pending_flush_task and not _pending_flush_task.done():
        _pending_flush_task.cancel()
        try:
            await _pending_flush_task
        except asyncio.CancelledError:
            pass
        _pending_flush_task = None
    if _bot_start_task and not _bot_start_task.done():
        _bot_start_task.cancel()
        try:
            await _bot_start_task
        except asyncio.CancelledError:
            pass
        _bot_start_task = None
    if _bot_app:
        try:
            await _bot_app.updater.stop()
            await _bot_app.stop()
            await _bot_app.shutdown()
        except Exception as exc:
            logger.warning("Error stopping Telegram bot: %s", exc)
        _bot_app = None

