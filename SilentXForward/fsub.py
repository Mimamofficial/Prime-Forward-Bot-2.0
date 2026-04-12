"""
SilentXForward/fsub.py
──────────────────────
Force Subscribe system.
Checks if user has joined all required channels before using the bot.
"""

import logging
from pyrogram import Client, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate
from config import FSUB_CHANNELS, OWNER_ID

logger = logging.getLogger(__name__)


async def check_fsub(client: Client, user_id: int) -> list:
    """
    Check which channels user has NOT joined.
    Returns list of unjoined channel dicts.
    Owner is always exempt.
    """
    if not FSUB_CHANNELS:
        return []

    # Owner bypass
    if OWNER_ID and user_id == OWNER_ID:
        return []

    not_joined = []
    for ch in FSUB_CHANNELS:
        try:
            member = await client.get_chat_member(ch["id"], user_id)
            # Check if banned/left
            if member.status in (
                enums.ChatMemberStatus.BANNED,
                enums.ChatMemberStatus.LEFT,
            ):
                not_joined.append(ch)
        except UserNotParticipant:
            not_joined.append(ch)
        except (ChatAdminRequired, ChannelPrivate):
            # Can't check — skip this channel
            logger.warning(f"Cannot check membership for channel {ch['id']} — bot may not be admin")
        except Exception as e:
            logger.warning(f"FSUB check error for {ch['id']}: {e}")

    return not_joined


async def send_fsub_message(client, message, not_joined: list):
    """Send the force subscribe message with join buttons."""

    # Build join buttons
    buttons = []
    for i, ch in enumerate(not_joined, 1):
        try:
            chat = await client.get_chat(ch["id"])
            title = chat.title or f"Channel {i}"
        except Exception:
            title = f"Channel {i}"

        link = ch.get("link")
        if not link:
            # Try to get invite link
            try:
                link = await client.export_chat_invite_link(ch["id"])
            except Exception:
                link = "https://t.me"

        buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=link)])

    # Add verify button
    buttons.append([InlineKeyboardButton("✅ I've Joined — Verify", callback_data="fsub_verify")])

    markup = InlineKeyboardMarkup(buttons)

    total   = len(FSUB_CHANNELS)
    pending = len(not_joined)
    done    = total - pending

    await message.reply_text(
        f"👋 <b>Hey {message.from_user.first_name}!</b>\n\n"
        f"⚠️ <b>Access Restricted!</b>\n\n"
        f"To use this bot, you must join <b>{total}</b> channel(s) first.\n\n"
        f"📊 Progress: <b>{done}/{total}</b> joined\n\n"
        f"👇 <b>Join the channels below:</b>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=markup
    )


async def fsub_verify_callback(client, callback_query):
    """Handle the verify button click."""
    user_id    = callback_query.from_user.id
    not_joined = await check_fsub(client, user_id)

    if not not_joined:
        # All joined!
        await callback_query.answer("✅ Verified! You can now use the bot.", show_alert=True)
        await callback_query.message.delete()
    else:
        total   = len(FSUB_CHANNELS)
        pending = len(not_joined)
        done    = total - pending

        # Rebuild buttons for remaining channels
        buttons = []
        for i, ch in enumerate(not_joined, 1):
            try:
                chat = await client.get_chat(ch["id"])
                title = chat.title or f"Channel {i}"
            except Exception:
                title = f"Channel {i}"

            link = ch.get("link")
            if not link:
                try:
                    link = await client.export_chat_invite_link(ch["id"])
                except Exception:
                    link = "https://t.me"

            buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=link)])

        buttons.append([InlineKeyboardButton("✅ I've Joined — Verify", callback_data="fsub_verify")])

        await callback_query.answer(
            f"❌ Still {pending} channel(s) pending! Please join all.",
            show_alert=True
        )
        await callback_query.message.edit_text(
            f"👋 <b>Hey {callback_query.from_user.first_name}!</b>\n\n"
            f"⚠️ <b>Still not joined all channels!</b>\n\n"
            f"📊 Progress: <b>{done}/{total}</b> joined\n\n"
            f"👇 <b>Join remaining channels:</b>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
