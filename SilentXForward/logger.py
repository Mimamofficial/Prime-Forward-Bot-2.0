"""
SilentXForward/logger.py
────────────────────────
Central log sender — sends formatted log messages to LOG_CHANNEL.
Import send_log() wherever you need to log an event.
"""

import logging
from datetime import datetime
from config import LOG_CHANNEL

logger = logging.getLogger(__name__)


async def send_log(client, text: str):
    """Send a log message to LOG_CHANNEL. Silently ignores if not configured."""
    if not LOG_CHANNEL:
        return
    try:
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=text,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.warning(f"Log send failed: {e}")


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


# ─── Event formatters ─────────────────────────────────────────────────────────

async def log_new_user(client, user):
    """Log when a new user starts the bot."""
    text = (
        f"👤 <b>New User Started Bot</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📛 Username: @{user.username or 'N/A'}\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_login(client, user, phone: str):
    """Log when a user logs in with their Telegram account."""
    text = (
        f"🔑 <b>User Login</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📛 Username: @{user.username or 'N/A'}\n"
        f"📱 Phone: <code>{phone}</code>\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_logout(client, user):
    """Log when a user logs out."""
    text = (
        f"🚪 <b>User Logout</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        f"📛 Username: @{user.username or 'N/A'}\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_source_added(client, user, source_title: str, source_id: int,
                            target_title: str, target_id: int):
    """Log when a source→target mapping is created."""
    text = (
        f"✅ <b>Source → Target Added</b>\n\n"
        f"👤 User: {user.first_name} (<code>{user.id}</code>)\n"
        f"📥 Source: <b>{source_title}</b>\n"
        f"   <code>{source_id}</code>\n"
        f"📤 Target: <b>{target_title}</b>\n"
        f"   <code>{target_id}</code>\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_source_removed(client, user, source_title: str, source_id: int):
    """Log when a source is fully removed."""
    text = (
        f"🗑️ <b>Source Removed</b>\n\n"
        f"👤 User: {user.first_name} (<code>{user.id}</code>)\n"
        f"📥 Source: <b>{source_title}</b>\n"
        f"   <code>{source_id}</code>\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_target_removed(client, user, source_title: str, source_id: int,
                              target_title: str, target_id: int):
    """Log when a specific target is removed from a source."""
    text = (
        f"➖ <b>Target Removed</b>\n\n"
        f"👤 User: {user.first_name} (<code>{user.id}</code>)\n"
        f"📥 Source: <b>{source_title}</b> (<code>{source_id}</code>)\n"
        f"🗑️ Target: <b>{target_title}</b> (<code>{target_id}</code>)\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_forward_success(client, source_title: str, source_id: int,
                               target_id: int, msg_count: int):
    """Log when messages are successfully forwarded."""
    text = (
        f"📨 <b>Forward Success</b>\n\n"
        f"📥 Source: <b>{source_title}</b>\n"
        f"   <code>{source_id}</code>\n"
        f"📤 Target: <code>{target_id}</code>\n"
        f"📊 Messages: <b>{msg_count}</b>\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)


async def log_forward_failed(client, source_id: int, target_id: int,
                              msg_count: int, error: str):
    """Log when forwarding fails."""
    text = (
        f"❌ <b>Forward Failed</b>\n\n"
        f"📥 Source: <code>{source_id}</code>\n"
        f"📤 Target: <code>{target_id}</code>\n"
        f"📊 Messages: <b>{msg_count}</b>\n"
        f"⚠️ Error: <code>{error[:200]}</code>\n"
        f"🕐 Time: {now()}"
    )
    await send_log(client, text)
