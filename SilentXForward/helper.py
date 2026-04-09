import logging
from SilentXForward import database
from SilentXForward.logger import (
    log_new_user, log_login, log_logout,
    log_source_added, log_source_removed, log_target_removed
)
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, PasswordHashInvalid, PeerIdInvalid,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START_IMAGE = "https://files.catbox.moe/x4fufo.jpg"

START_TEXT = """<b>🎬 Prime Forward Bot

<i>Your Ultimate Auto Forwarding System 🚀</i>

━━━━━━━━━━━━━━━
⚡ Smart Features:
• Multi Source ➜ Multi Target
• Auto Video / File Forward
• Private Channel Support 🔐
• Fast • Secure • Reliable

━━━━━━━━━━━━━━━
🎯 Get Started:
➤ /login (for private access)
➤ /set source target
➤ Sit back & enjoy automation 😎

<blockquote>👨‍💻 Maintained by <a href="https://t.me/Mrn_Officialx">Mrn Official</a></blockquote>

🔥 Experience Next Level Forwarding</b>
"""

HELP_TEXT = """<b>⭐ Auto Forward Bot (Master Edition) ⭐

🔑 Session:
/login | /logout | /cancel | /session

📡 Forwarding:
/on | /off | /resume | /status

⚙️ Settings:
/setdelay [Sec] | /skip

🔍 Filter:
/addfilter [word] | /remfilter [word] | /listfilters

✍️ Footer:
/endtext [Text] | /remendtext | /listendtext

📊 Management:
/set &lt;source&gt; &lt;target&gt; | /remove_target | /remove_source | /list | /clear

📈 Stats:
/count

👑 Admin:
/addadmin | /ban | /unban | /removeuser</b>

<b>Channel: @Mrn_Officialx</b>
"""

ABOUT_TEXT = """<b><blockquote>╭────[ ᴍʏ ᴅᴇᴛᴀɪʟs ]────⍟</blockquote>
<blockquote>├⍟ 🎭 Mʏ Nᴀᴍᴇ : <a href='https://t.me/Prime_Forwards_Bot'>𝗣𝗿𝗶𝗺𝗲 𝗙𝗼𝗿𝘄𝗮𝗿𝗱 𝗕𝗼𝘁</a></blockquote>
<blockquote>├⍟ 🇮🇳 Cʀᴇᴀᴛᴏʀ : <a href='https://t.me/mimam_officialx/'>𝄟͢🦋⃟≛⃝ 𝐌𝐮𝐳𝐚𝐟𝐟𝐚𝐫 𝄟⃝❤</a></blockquote>
<blockquote>├⍟ 📚 Lɪʙʀᴀʀʏ : <a href='https://docs.pyrogram.org/'>ᴘʏʀᴏɢʀᴀᴍ</a></blockquote>
<blockquote>├⍟ 🍿 Lᴀɴɢᴜᴀɢᴇ : <a href='https://www.python.org/download/releases/3.0/'>ᴘʏᴛʜᴏɴ 𝟹</a></blockquote>
<blockquote>├⍟ 🐍 DᴀᴛᴀBᴀsᴇ : <a href='https://www.mongodb.com/'>ᴍᴏɴɢᴏ ᴅʙ</a></blockquote>
<blockquote>├⍟ ⚙️ Bᴏᴛ Sᴇʀᴠᴇʀ : <a href='https://heroku.com/'>ʜᴇʀᴏᴋᴜ</a></blockquote>
<blockquote>├⍟ 🥶 Bᴜɪʟᴅ Sᴛᴀᴛᴜs : ᴠ𝟹.𝟶 [ ꜱᴛᴀʙʟᴇ ]</blockquote>
<blockquote>├⍟ Multi-Source to Multi-Target ✅</blockquote>
<blockquote>├⍟ All Media Types ✅</blockquote>
<blockquote>├⍟ Forwarding ON/OFF ✅</blockquote>
<blockquote>├⍟ Custom Delay ✅</blockquote>
<blockquote>├⍟ Keyword Filter ✅</blockquote>
<blockquote>├⍟ Footer Text ✅</blockquote>
<blockquote>├⍟ Admin System ✅</blockquote>
<blockquote>├⍟ Stats & Count ✅</blockquote>
<blockquote>├⍟ Userbot Login ✅</blockquote>
<blockquote>├⍟ Log Channel ✅</blockquote>
<blockquote>╰───────────────⍟</b></blockquote>"""

BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("📢 Channel", url="https://t.me/Mrn_Officialx"),
    InlineKeyboardButton("🥰 𝄟͢🦋⃟≛⃝ 𝐌𝐮𝐳𝐚𝐟𝐟𝐚𝐫 𝄟⃝❤", url="https://t.me/mimam_officialx")
]])

login_states = {}


# ==================== HELPERS ====================

async def smart_get_chat(client, chat_id, user_id):
    from SilentXForward.forward import active_userbots
    ub = active_userbots.get(user_id)
    if ub and ub.is_connected:
        try:
            return await ub.get_chat(chat_id)
        except PeerIdInvalid:
            logger.info(f"PeerIdInvalid for {chat_id} — trying dialogs...")
            try:
                async for dialog in ub.get_dialogs():
                    if dialog.chat.id == int(chat_id):
                        return dialog.chat
            except Exception as e:
                logger.warning(f"Dialog iteration failed: {e}")
            try:
                return await ub.get_chat(chat_id)
            except Exception as e:
                logger.warning(f"Userbot still can't get {chat_id}: {e}")
        except Exception as e:
            logger.warning(f"Userbot get_chat failed ({chat_id}): {e}")
    return await client.get_chat(chat_id)


# ==================== START / HELP / ABOUT ====================

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    try:
        await log_new_user(client, message.from_user)
        await message.reply_photo(photo=START_IMAGE, caption=START_TEXT,
                                  parse_mode=enums.ParseMode.HTML, reply_markup=BUTTONS)
    except Exception as e:
        logger.error(f"Start error: {e}")
        try:
            await message.reply(text=START_TEXT, parse_mode=enums.ParseMode.HTML,
                                reply_markup=BUTTONS, disable_web_page_preview=True)
        except Exception:
            pass

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    await message.reply(text=HELP_TEXT, parse_mode=enums.ParseMode.HTML,
                        reply_markup=BUTTONS, disable_web_page_preview=True)

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client, message):
    await message.reply(text=ABOUT_TEXT, parse_mode=enums.ParseMode.HTML,
                        reply_markup=BUTTONS, disable_web_page_preview=True)


# ==================== FORWARDING ON / OFF / RESUME ====================

@Client.on_message(filters.command("off") & filters.private)
async def cmd_off(client, message: Message):
    await database.set_forwarding(message.from_user.id, False)
    await message.reply_text("⏸️ <b>Forwarding paused!</b>\n\nResume karne ke liye /on ya /resume use karo.",
                             parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["on", "resume"]) & filters.private)
async def cmd_on(client, message: Message):
    await database.set_forwarding(message.from_user.id, True)
    await message.reply_text("▶️ <b>Forwarding resumed!</b>\n\nMessages ab forward honge.",
                             parse_mode=enums.ParseMode.HTML)


# ==================== STATUS ====================

@Client.on_message(filters.command("status") & filters.private)
async def cmd_status(client, message: Message):
    user_id  = message.from_user.id
    settings = await database.get_all_settings(user_id)
    mappings = await database.get_user_mappings(user_id)
    count    = await database.get_forward_count(user_id)
    fwd_on   = settings.get("forwarding_enabled", True)
    delay    = settings.get("delay", 0.1)
    endtext  = settings.get("endtext", "Not set")
    fil_list = settings.get("filters", [])

    from SilentXForward.forward import active_userbots
    ub = active_userbots.get(user_id)
    session_status = "🟢 Active" if (ub and ub.is_connected) else "🔴 Not logged in"

    text = (
        f"<b>📊 Status Dashboard</b>\n\n"
        f"👤 Session: {session_status}\n"
        f"📡 Forwarding: {'▶️ ON' if fwd_on else '⏸️ OFF'}\n"
        f"⏱️ Delay: <code>{delay}s</code>\n"
        f"📊 Total Forwarded: <b>{count}</b>\n"
        f"🗂️ Sources: <b>{len(mappings)}</b>\n"
        f"🔍 Filters: <b>{len(fil_list)}</b> {('— ' + ', '.join(fil_list)) if fil_list else ''}\n"
        f"✍️ Footer: <code>{endtext[:50] if endtext != 'Not set' else 'Not set'}</code>"
    )
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ==================== SETDELAY ====================

@Client.on_message(filters.command("setdelay") & filters.private)
async def cmd_setdelay(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/setdelay 2</code>\n\nDelay in seconds (0.1 to 60)",
            parse_mode=enums.ParseMode.HTML
        )
    try:
        delay = float(message.command[1])
        if delay < 0 or delay > 60:
            raise ValueError
        await database.set_delay(message.from_user.id, delay)
        await message.reply_text(
            f"⏱️ <b>Delay set to {delay}s!</b>\n\nAb har message ke baad {delay} second wait hoga.",
            parse_mode=enums.ParseMode.HTML
        )
    except ValueError:
        await message.reply_text("<b>❌ Valid number do (0.1 - 60)</b>", parse_mode=enums.ParseMode.HTML)


# ==================== SKIP (manual skip — clears buffer) ====================

@Client.on_message(filters.command("skip") & filters.private)
async def cmd_skip(client, message: Message):
    from SilentXForward.forward import message_buffer, buffer_tasks
    cleared = 0
    for cid in list(message_buffer.keys()):
        message_buffer[cid].clear()
        cleared += 1
        t = buffer_tasks.get(cid)
        if t and not t.done():
            t.cancel()
    await message.reply_text(
        f"⏭️ <b>Skipped!</b> {cleared} pending buffer(s) cleared.",
        parse_mode=enums.ParseMode.HTML
    )


# ==================== FILTERS ====================

@Client.on_message(filters.command("addfilter") & filters.private)
async def cmd_addfilter(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/addfilter word</code>\n\nSirf wahi messages forward honge jisme yeh word ho.",
            parse_mode=enums.ParseMode.HTML
        )
    word = " ".join(message.command[1:]).lower().strip()
    added = await database.add_filter(message.from_user.id, word)
    if added:
        await message.reply_text(f"✅ <b>Filter added:</b> <code>{word}</code>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(f"⚠️ <b>Already exists:</b> <code>{word}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("remfilter") & filters.private)
async def cmd_remfilter(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/remfilter word</code>", parse_mode=enums.ParseMode.HTML
        )
    word = " ".join(message.command[1:]).lower().strip()
    removed = await database.remove_filter(message.from_user.id, word)
    if removed:
        await message.reply_text(f"🗑️ <b>Filter removed:</b> <code>{word}</code>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(f"⚠️ <b>Not found:</b> <code>{word}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("listfilters") & filters.private)
async def cmd_listfilters(client, message: Message):
    fil_list = await database.get_filters(message.from_user.id)
    if not fil_list:
        return await message.reply_text("🔍 <b>No filters set.</b>\n\nUse /addfilter to add one.",
                                        parse_mode=enums.ParseMode.HTML)
    text = "<b>🔍 Active Filters:</b>\n\n"
    for i, w in enumerate(fil_list, 1):
        text += f"{i}. <code>{w}</code>\n"
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ==================== END TEXT / FOOTER ====================

@Client.on_message(filters.command("endtext") & filters.private)
async def cmd_endtext(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/endtext Your footer text here</code>",
            parse_mode=enums.ParseMode.HTML
        )
    text = message.text.split(None, 1)[1]
    await database.set_endtext(message.from_user.id, text)
    await message.reply_text(
        f"✍️ <b>Footer set:</b>\n<code>{text}</code>",
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("remendtext") & filters.private)
async def cmd_remendtext(client, message: Message):
    await database.remove_endtext(message.from_user.id)
    await message.reply_text("🗑️ <b>Footer removed!</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("listendtext") & filters.private)
async def cmd_listendtext(client, message: Message):
    endtext = await database.get_endtext(message.from_user.id)
    if not endtext:
        return await message.reply_text("✍️ <b>No footer set.</b>\n\nUse /endtext to add one.",
                                        parse_mode=enums.ParseMode.HTML)
    await message.reply_text(f"✍️ <b>Current Footer:</b>\n\n<code>{endtext}</code>",
                             parse_mode=enums.ParseMode.HTML)


# ==================== STATS ====================

@Client.on_message(filters.command("count") & filters.private)
async def cmd_count(client, message: Message):
    count = await database.get_forward_count(message.from_user.id)
    await message.reply_text(
        f"📊 <b>Forward Stats</b>\n\n"
        f"✅ Total Forwarded: <b>{count}</b> messages\n\n"
        f"Reset karne ke liye /resetcount use karo.",
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("resetcount") & filters.private)
async def cmd_resetcount(client, message: Message):
    await database.reset_forward_count(message.from_user.id)
    await message.reply_text("🔄 <b>Count reset!</b>", parse_mode=enums.ParseMode.HTML)


# ==================== ADMIN SYSTEM ====================

@Client.on_message(filters.command("addadmin") & filters.private)
async def cmd_addadmin(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/addadmin user_id</code>", parse_mode=enums.ParseMode.HTML
        )
    try:
        target_id = int(message.command[1])
        await database.add_admin(message.from_user.id, target_id)
        await message.reply_text(
            f"👑 <b>Admin added:</b> <code>{target_id}</code>", parse_mode=enums.ParseMode.HTML
        )
    except ValueError:
        await message.reply_text("<b>❌ Valid user_id do.</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("removeuser") & filters.private)
async def cmd_removeuser(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/removeuser user_id</code>", parse_mode=enums.ParseMode.HTML
        )
    try:
        target_id = int(message.command[1])
        removed = await database.remove_admin(message.from_user.id, target_id)
        if removed:
            await message.reply_text(
                f"✅ <b>Admin removed:</b> <code>{target_id}</code>", parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(f"⚠️ <b>Not found in admins.</b>", parse_mode=enums.ParseMode.HTML)
    except ValueError:
        await message.reply_text("<b>❌ Valid user_id do.</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("ban") & filters.private)
async def cmd_ban(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/ban user_id</code>", parse_mode=enums.ParseMode.HTML
        )
    try:
        target_id = int(message.command[1])
        await database.ban_user(message.from_user.id, target_id)
        await message.reply_text(
            f"🚫 <b>User banned:</b> <code>{target_id}</code>", parse_mode=enums.ParseMode.HTML
        )
    except ValueError:
        await message.reply_text("<b>❌ Valid user_id do.</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("unban") & filters.private)
async def cmd_unban(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/unban user_id</code>", parse_mode=enums.ParseMode.HTML
        )
    try:
        target_id = int(message.command[1])
        unbanned = await database.unban_user(message.from_user.id, target_id)
        if unbanned:
            await message.reply_text(
                f"✅ <b>User unbanned:</b> <code>{target_id}</code>", parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text("⚠️ <b>User not in ban list.</b>", parse_mode=enums.ParseMode.HTML)
    except ValueError:
        await message.reply_text("<b>❌ Valid user_id do.</b>", parse_mode=enums.ParseMode.HTML)


# ==================== CHANNEL MANAGEMENT ====================

@Client.on_message(filters.command("set") & filters.private)
async def set_channels(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/set &lt;source_id&gt; &lt;target_id&gt;</code>",
            parse_mode=enums.ParseMode.HTML
        )
    proc_msg = await message.reply_text("⏳ Processing...")
    try:
        source_chat = await smart_get_chat(client, message.command[1], user_id)
        target_chat = await smart_get_chat(client, message.command[2], user_id)
        result = await database.add_target_to_source(
            user_id, source_chat.id, target_chat.id, source_chat.title, target_chat.title
        )
        await proc_msg.delete()
        if result in ("created", "added"):
            action = "New Source Created" if result == "created" else "Target Added"
            await message.reply_text(
                f"<b>✅ {action}:</b>\n\n"
                f"📥 Source: {source_chat.title}\n   <code>{source_chat.id}</code>\n\n"
                f"📤 Target: {target_chat.title}\n   <code>{target_chat.id}</code>\n\n"
                f"🎉 Messages Will Be Forwarded!",
                parse_mode=enums.ParseMode.HTML
            )
            await log_source_added(client, message.from_user,
                                   source_chat.title, source_chat.id,
                                   target_chat.title, target_chat.id)
        else:
            await message.reply_text("<b>⚠️ Already Exists!</b>", parse_mode=enums.ParseMode.HTML)
    except PeerIdInvalid:
        await proc_msg.delete()
        await message.reply_text(
            "<b>❌ PEER_ID_INVALID!</b>\n\n"
            "Apne Telegram se <b>dono channels ek baar kholo</b> phir /set try karo.",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        await proc_msg.delete()
        await message.reply_text(
            f"<b>❌ Error:</b> <code>{e}</code>\n\n/session se check karo.",
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("remove_target") & filters.private)
async def remove_target_channel(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/remove_target &lt;source_id&gt; &lt;target_id&gt;</code>",
            parse_mode=enums.ParseMode.HTML
        )
    try:
        source_chat = await smart_get_chat(client, message.command[1], user_id)
        target_chat = await smart_get_chat(client, message.command[2], user_id)
        result = await database.remove_target_from_source(user_id, source_chat.id, target_chat.id)
        if result == "removed":
            await message.reply_text(
                f"✅ <b>Target Removed!</b>\n\n"
                f"📥 {source_chat.title} (<code>{source_chat.id}</code>)\n"
                f"🗑️ {target_chat.title} (<code>{target_chat.id}</code>)",
                parse_mode=enums.ParseMode.HTML
            )
            await log_target_removed(client, message.from_user,
                                     source_chat.title, source_chat.id,
                                     target_chat.title, target_chat.id)
        else:
            await message.reply_text("<b>⚠️ Not Found.</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"<b>❌ Error:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("remove_source") & filters.private)
async def remove_channel(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Usage:</b> <code>/remove_source &lt;source_id&gt;</code>",
            parse_mode=enums.ParseMode.HTML
        )
    try:
        chat = await smart_get_chat(client, message.command[1], user_id)
        removed = await database.remove_source(user_id, chat.id)
        if removed:
            await message.reply_text(
                f"✅ <b>Removed:</b> {chat.title} (<code>{chat.id}</code>)",
                parse_mode=enums.ParseMode.HTML
            )
            await log_source_removed(client, message.from_user, chat.title, chat.id)
        else:
            await message.reply_text(f"⚠️ Not found.", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"<b>❌ Error:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("list") & filters.private)
async def list_mappings(client, message: Message):
    user_id  = message.from_user.id
    mappings = await database.get_user_mappings(user_id)
    if not mappings:
        return await message.reply_text(
            "<b>❌ No mappings found!</b>\n\nUse /set to create one.",
            parse_mode=enums.ParseMode.HTML
        )
    text = "<b>📊 Your Channel Mappings:</b>\n\n"
    for idx, mapping in enumerate(mappings, 1):
        source_id  = mapping['source_id']
        target_ids = mapping.get('target_ids', [])
        try:
            sc = await smart_get_chat(client, source_id, user_id)
            text += f"<b>{idx}. 📥 {sc.title}</b>\n   <code>{source_id}</code>\n   ⤵️ Targets ({len(target_ids)}):\n"
            for tid in target_ids:
                try:
                    tc = await smart_get_chat(client, tid, user_id)
                    text += f"   • {tc.title} (<code>{tid}</code>)\n"
                except:
                    text += f"   • <code>{tid}</code>\n"
            text += "\n"
        except:
            text += f"<b>{idx}.</b> <code>{source_id}</code> — {len(target_ids)} target(s)\n\n"
    text += f"<b>Total Sources:</b> {len(mappings)}"
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("clear") & filters.private)
async def clear_all(client, message: Message):
    count = await database.clear_all_mappings(message.from_user.id)
    if count > 0:
        await message.reply_text(f"<b>✅ Cleared {count} source(s)!</b>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text("<b>❌ No mappings to clear!</b>", parse_mode=enums.ParseMode.HTML)


# ==================== USERBOT LOGIN ====================

@Client.on_message(filters.command("login") & filters.private)
async def cmd_login(client, message: Message):
    user_id  = message.from_user.id
    existing = await database.get_userbot_session(user_id)
    if existing:
        return await message.reply_text(
            f"<b>✅ Already logged in!</b>\n\n📱 <code>{existing.get('phone','N/A')}</code>\n"
            f"🕐 {existing.get('created_at','N/A')}\n\n/logout | /session",
            parse_mode=enums.ParseMode.HTML
        )
    login_states[user_id] = {"step": "phone"}
    await message.reply_text(
        "<b>🔑 Userbot Login</b>\n\nPhone number bhejein.\nFormat: <code>+919876543210</code>\n\n❌ /cancel",
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("logout") & filters.private)
async def cmd_logout(client, message: Message):
    user_id = message.from_user.id
    from SilentXForward.forward import active_userbots
    ub = active_userbots.get(user_id)
    if ub:
        try:
            await ub.stop()
        except Exception:
            pass
        active_userbots.pop(user_id, None)
    deleted = await database.delete_userbot_session(user_id)
    if deleted:
        await log_logout(client, message.from_user)
        await message.reply_text("<b>✅ Logged out!</b>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text("<b>⚠️ Already logged out.</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("session") & filters.private)
async def cmd_session(client, message: Message):
    user_id = message.from_user.id
    session = await database.get_userbot_session(user_id)
    if not session:
        return await message.reply_text(
            "<b>❌ No active session.</b>\n\n/login se connect karein.",
            parse_mode=enums.ParseMode.HTML
        )
    from SilentXForward.forward import active_userbots
    ub     = active_userbots.get(user_id)
    status = "🟢 Active" if (ub and ub.is_connected) else "🔴 Inactive (restart bot)"
    await message.reply_text(
        f"<b>📋 Session Info</b>\n\n👤 {status}\n📱 <code>{session.get('phone','N/A')}</code>\n"
        f"🕐 {session.get('created_at','N/A')}\n\n/logout",
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("cancel") & filters.private)
async def cmd_cancel(client, message: Message):
    user_id = message.from_user.id
    if user_id in login_states:
        tc = login_states[user_id].get("temp_client")
        if tc:
            try:
                await tc.disconnect()
            except Exception:
                pass
        del login_states[user_id]
        await message.reply_text("<b>❌ Login cancelled.</b>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text("<b>⚠️ No active login.</b>", parse_mode=enums.ParseMode.HTML)


# ==================== LOGIN STEP HANDLER ====================

@Client.on_message(
    filters.private & filters.text &
    ~filters.command(["login","logout","session","cancel","start","help","about",
                      "set","remove_target","remove_source","list","clear",
                      "on","off","resume","status","setdelay","skip",
                      "addfilter","remfilter","listfilters",
                      "endtext","remendtext","listendtext",
                      "count","resetcount","addadmin","removeuser","ban","unban"])
)
async def login_step_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in login_states:
        return

    state = login_states[user_id]
    step  = state.get("step")

    # ── Phone ──────────────────────────────────────────────────────────────
    if step == "phone":
        phone = message.text.strip()
        msg   = await message.reply_text("⏳ OTP bhej raha hoon...")
        import config as cfg
        temp_client = Client(f"temp_{user_id}", api_id=cfg.API_ID, api_hash=cfg.API_HASH, in_memory=True)
        try:
            await temp_client.connect()
            sent = await temp_client.send_code(phone)
            state.update({"step":"otp","phone":phone,
                          "phone_code_hash":sent.phone_code_hash,"temp_client":temp_client})
            login_states[user_id] = state
            await msg.edit("<b>📩 OTP bheja!</b>\n\nFormat: <code>1 2 3 4 5</code>\n\n❌ /cancel",
                           parse_mode=enums.ParseMode.HTML)
        except PhoneNumberInvalid:
            await temp_client.disconnect()
            del login_states[user_id]
            await msg.edit("<b>❌ Invalid number!</b>\nFormat: <code>+919876543210</code>",
                           parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            await temp_client.disconnect()
            del login_states[user_id]
            await msg.edit(f"<b>❌ Error:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)

    # ── OTP ────────────────────────────────────────────────────────────────
    elif step == "otp":
        otp = message.text.strip().replace(" ","")
        temp_client = state.get("temp_client")
        try:
            await temp_client.sign_in(state["phone"], state["phone_code_hash"], otp)
            ss = await temp_client.export_session_string()
            await temp_client.disconnect()
            await database.save_userbot_session(user_id, ss, state["phone"])
            del login_states[user_id]
            from SilentXForward.forward import start_single_userbot
            await start_single_userbot(user_id, ss)
            await log_login(client, message.from_user, state["phone"])
            await message.reply_text(
                "<b>✅ Login Successful!</b>\n\n🤖 Userbot started!\n\n"
                "<b>⚠️ Important:</b> Apne account se <b>source/target channels ek baar kholo</b> "
                "phir /set karo.\n\n📋 /session | 🚪 /logout",
                parse_mode=enums.ParseMode.HTML
            )
        except PhoneCodeInvalid:
            await message.reply_text("<b>❌ Galat OTP!</b>", parse_mode=enums.ParseMode.HTML)
        except PhoneCodeExpired:
            await temp_client.disconnect()
            del login_states[user_id]
            await message.reply_text("<b>⏰ OTP expire!</b> Dobara /login.", parse_mode=enums.ParseMode.HTML)
        except SessionPasswordNeeded:
            state["step"] = "password"
            login_states[user_id] = state
            await message.reply_text("<b>🔐 2FA Password bhejein:</b>\n\n❌ /cancel",
                                     parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_states[user_id]
            await message.reply_text(f"<b>❌ Error:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)

    # ── 2FA ────────────────────────────────────────────────────────────────
    elif step == "password":
        temp_client = state.get("temp_client")
        try:
            await temp_client.check_password(message.text.strip())
            ss = await temp_client.export_session_string()
            await temp_client.disconnect()
            await database.save_userbot_session(user_id, ss, state["phone"])
            del login_states[user_id]
            from SilentXForward.forward import start_single_userbot
            await start_single_userbot(user_id, ss)
            await log_login(client, message.from_user, state["phone"])
            await message.reply_text(
                "<b>✅ Login Successful! (2FA)</b>\n\n🤖 Userbot started!\n\n📋 /session | 🚪 /logout",
                parse_mode=enums.ParseMode.HTML
            )
        except PasswordHashInvalid:
            await message.reply_text("<b>❌ Galat password!</b>", parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_states[user_id]
            await message.reply_text(f"<b>❌ Error:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)
