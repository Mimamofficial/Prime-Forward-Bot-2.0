import logging
from SilentXForward import database
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START_TEXT = """<b>👋ʜᴇʟʟᴏ! ɪ ᴀᴍ ᴍʀɴ_ғᴏʀᴡᴀʀᴅ_ʙᴏᴛ.\n\nɪ ᴄᴀɴ ғᴏʀᴡᴀʀᴅ ᴠɪᴅᴇᴏs ᴀɴᴅ ᴅᴏᴄᴜᴍᴇɴᴛs ғʀᴏᴍ ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴍᴜʟᴛɪᴘʟᴇ ᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟs, ғɪʟᴛᴇʀɪɴɢ ᴏᴜᴛ ᴜɴᴡᴀɴᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ.!! 😍\n<blockquote>🌿 ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ : <a href="https://t.me/Mrn_Officialx">Mrn_Officialx</a></blockquote></b>"""

HELP_TEXT = """<b>ℹ️ Help Menu

I Am An Auto-Forward Bot. I Forward Files From Source Channels To Target Channels.</b>

<b>Commands:
/start - Check If I Am Alive.
/help - Show This Help Message.
/about - Show Information About Me.
/set &lt;source_id&gt; &lt;target_id&gt; - Add Target To Source
/remove_target &lt;source_id&gt; &lt;target_id&gt; - Remove A Target From Source
/remove_source &lt;source_id&gt; - Remove Source
/list - View All Set Channels 
/clear - Clear All Mappings

🔑 Userbot Login (Private Channels):
/login - Login with your Telegram account
/logout - Logout & remove your session
/session - Check your login status
/cancel - Cancel ongoing login process</b>

<b>How to use:
1. Use /login to connect your Telegram account (for private channels).
2. Add Me To Source Channels And Target Channels As Admin (for public channels).
3. Use /set command to link source to target channels.
4. I Will Automatically Forward Videos And Documents!</b>

<b>Channel: @Mrn_Officialx</b>
"""

ABOUT_TEXT = """<b><blockquote>╭────[ ᴍʏ ᴅᴇᴛᴀɪʟs ]────⍟</blockquote>
<blockquote>├⍟ 🎭 Mʏ Nᴀᴍᴇ : <a href='https://t.me/MRN_ForwardXBot/'>ᴍʀɴ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</a></blockquote>
<blockquote>├⍟ 🇮🇳 Cʀᴇᴀᴛᴏʀ : <a href='https://t.me/mimam_officialx/'>𝄟͢🦋⃟≛⃝ 𝐌𝐮𝐳𝐚𝐟𝐟𝐚𝐫 𝄟⃝❤</a></blockquote>
<blockquote>├⍟ 📚 Lɪʙʀᴀʀʏ : <a href='https://docs.pyrogram.org/'>ᴘʏʀᴏɢʀᴀᴍ</a></blockquote>
<blockquote>├⍟ 🍿 Lᴀɴɢᴜᴀɢᴇ : <a href='https://www.python.org/download/releases/3.0/'>ᴘʏᴛʜᴏɴ 𝟹</a></blockquote>
<blockquote>├⍟ 🐍 DᴀᴛᴀBᴀsᴇ : <a href='https://www.mongodb.com/'>ᴍᴏɴɢᴏ ᴅʙ</a></blockquote>
<blockquote>├⍟ ⚙️ Bᴏᴛ Sᴇʀᴠᴇʀ : <a href='https://heroku.com/'>ʜᴇʀᴏᴋᴜ</a></blockquote>
<blockquote>├⍟ 🥶 Bᴜɪʟᴅ Sᴛᴀᴛᴜs : ᴠ𝟸.𝟶 [ ꜱᴛᴀʙʟᴇ ]</blockquote>
<blockquote>├⍟ Features:</blockquote>
<blockquote>├⍟ Multi-Source to Multi-Target</blockquote>
<blockquote>├⍟ Video & Document Filter</blockquote>
<blockquote>├⍟ FloodWait Handling</blockquote>
<blockquote>├⍟ MongoDB Database</blockquote>
<blockquote>├⍟ Queue System</blockquote>
<blockquote>├⍟ Userbot Session Login ✨</blockquote>
<blockquote>╰───────────────⍟</b></blockquote>"""

BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📢 Channel", url="https://t.me/Mrn_Officialx"),
            InlineKeyboardButton("🥰 𝄟͢🦋⃟≛⃝ 𝐌𝐮𝐳𝐚𝐟𝐟𝐚𝐫 𝄟⃝❤", url="https://t.me/mimam_officialx")
        ]
    ]
)

# ==================== LOGIN STATE TRACKER ====================
# { user_id: { "step": "phone"/"otp"/"password", "phone": ..., "phone_code_hash": ..., "temp_client": ... } }
login_states = {}

# ==================== EXISTING COMMANDS (unchanged) ====================

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    try:
        await message.reply(
            text=START_TEXT,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=BUTTONS,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error In Start Function: {e}")

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    try:
        await message.reply(
            text=HELP_TEXT,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=BUTTONS,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error In Help Function: {e}")

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client, message):
    try:
        await message.reply(
            text=ABOUT_TEXT,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=BUTTONS,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error In About Function: {e}")

@Client.on_message(filters.command("set") & filters.private)
async def set_channels(client, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 3:
        await message.reply_text(
            "<b>❌ Usage:</b> <code>/set &lt;source_id&gt; &lt;target_id&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/set -1001234567890 -1009876543210</code>",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    source = message.command[1]
    target = message.command[2]
    
    try:
        source_chat = await client.get_chat(source)
        target_chat = await client.get_chat(target)
        
        source_id = source_chat.id
        target_id = target_chat.id
        
        result = await database.add_target_to_source(
            user_id, 
            source_id, 
            target_id, 
            source_chat.title, 
            target_chat.title
        )
        
        if result == "created":
            await message.reply_text(
                f"<b>✅ New Source Created:</b>\n\n"
                f"<b>📥 Source:</b> {source_chat.title}\n"
                f"   <code>{source_id}</code>\n\n"
                f"<b>📤 Target:</b> {target_chat.title}\n"
                f"   <code>{target_id}</code>\n\n"
                f"🎉 Messages Will Be Forwarded!",
                parse_mode=enums.ParseMode.HTML
            )
        elif result == "added":
            await message.reply_text(
                f"<b>✅ Target Added:</b>\n\n"
                f"<b>📥 Source:</b> {source_chat.title}\n"
                f"   <code>{source_id}</code>\n\n"
                f"<b>📤 New Target:</b> {target_chat.title}\n"
                f"   <code>{target_id}</code>",
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                f"<b>⚠️ Already Exists:</b>\n\n"
                f"This Target Is Already Set For This Source!",
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        await message.reply_text(
            f"<b>❌ Error:</b> {e}\n\n"
            "Make sure:\n"
            "• Bot is admin in both channels\n"
            "• Channel IDs are correct",
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("remove_target") & filters.private)
async def remove_target_channel(client, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 3:
        await message.reply_text(
            "<b>❌ Usage:</b> <code>/rem &lt;source_id&gt; &lt;target_id&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/rem -1001234567890 -1009876543210</code>",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    source_input = message.command[1]
    target_input = message.command[2]
    
    try:
        source_chat = await client.get_chat(source_input)
        source_id = source_chat.id
        source_title = source_chat.title

        target_chat = await client.get_chat(target_input)
        target_id = target_chat.id
        target_title = target_chat.title
        
        result = await database.remove_target_from_source(user_id, source_id, target_id)
        
        if result == "removed":
            await message.reply_text(
                f"<b>✅ Target Removed Successfully!</b>\n\n"
                f"<b>📥 Source:</b> {source_title}\n"
                f"   <code>{source_id}</code>\n\n"
                f"<b>🗑️ Target:</b> {target_title}\n"
                f"   <code>{target_id}</code>\n\n"
                f"Target Channel Has Been Removed From This Source Mapping.",
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                f"<b>⚠️ Not Found:</b>\n\n"
                f"<b>📥 Source:</b> {source_title}\n"
                f"<b>🗑️ Target:</b> {target_title}\n\n"
                f"No Mapping Exists For This Source-target Pair.\n\n"
                f"Use <code>/list</code> To See Your Current Mappings.",
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        await message.reply_text(
            f"<b>❌ Error:</b> {e}\n\n"
            f"Make sure both channel IDs are valid and accessible.",
            parse_mode=enums.ParseMode.HTML
        )
        
@Client.on_message(filters.command("remove_source") & filters.private)
async def remove_channel(client, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        await message.reply_text(
            "<b>❌ Usage:</b> <code>/rem &lt;source_id&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/rem -1001234567890</code>",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    source = message.command[1]
    
    try:
        chat = await client.get_chat(source)
        source_id = chat.id
        
        removed = await database.remove_source(user_id, source_id)
        
        if removed:
            await message.reply_text(
                f"<b>✅ Removed:</b>\n\n"
                f"<b>📥 Source:</b> {chat.title}\n"
                f"   <code>{source_id}</code>\n\n"
                f"All Targets For This Source Have Been Removed.",
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                f"<b>⚠️ Not Found:</b>\n\n"
                f"No Targets Exists For <b>{chat.title}</b>\n\n"
                f"Use /list To See Your Mappings.",
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        await message.reply_text(
            f"<b>❌ Error:</b> {e}",
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("list") & filters.private)
async def list_mappings(client, message: Message):
    user_id = message.from_user.id
    
    mappings = await database.get_user_mappings(user_id)
    
    if not mappings:
        await message.reply_text(
            "<b>❌ No mappings found!</b>\n\n"
            "Use <code>/set &lt;source_id&gt; &lt;target_id&gt;</code> to create one.",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    text = "<b>📊 Your Channel Mappings:</b>\n\n"
    
    for idx, mapping in enumerate(mappings, 1):
        source_id = mapping['source_id']
        target_ids = mapping.get('target_ids', [])
        
        try:
            source_chat = await client.get_chat(source_id)
            text += f"<b>{idx}. 📥 {source_chat.title}</b>\n"
            text += f"   <code>{source_id}</code>\n"
            text += f"   ⤵️ <b>Targets ({len(target_ids)}):</b>\n"
            
            for target_id in target_ids:
                try:
                    target_chat = await client.get_chat(target_id)
                    text += f"   • {target_chat.title} (<code>{target_id}</code>)\n"
                except:
                    text += f"   • <code>{target_id}</code> (Unable to fetch)\n"
            
            text += "\n"
        except:
            text += f"<b>{idx}.</b> <code>{source_id}</code> (Unable to fetch)\n"
            text += f"   Targets: {len(target_ids)}\n\n"
    
    text += f"<b>Total Sources:</b> {len(mappings)}"
    
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("clear") & filters.private)
async def clear_all(client, message: Message):
    user_id = message.from_user.id
    
    count = await database.clear_all_mappings(user_id)
    
    if count > 0:
        await message.reply_text(
            f"<b>✅ Cleared {count} source(s)!</b>\n\n"
            f"All Your Mappings Have Been Removed.",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            "<b>❌ You Don't Have Any Mappings To Clear!</b>",
            parse_mode=enums.ParseMode.HTML
        )


# ==================== USERBOT LOGIN COMMANDS (NEW) ====================

@Client.on_message(filters.command("login") & filters.private)
async def cmd_login(client, message: Message):
    user_id = message.from_user.id

    # Check if already logged in
    existing = await database.get_userbot_session(user_id)
    if existing:
        return await message.reply_text(
            "<b>✅ Aap already login hain!</b>\n\n"
            f"📱 Phone: <code>{existing.get('phone', 'N/A')}</code>\n"
            f"🕐 Since: {existing.get('created_at', 'N/A')}\n\n"
            "Logout karne ke liye: /logout\n"
            "Status dekhne ke liye: /session",
            parse_mode=enums.ParseMode.HTML
        )

    login_states[user_id] = {"step": "phone"}
    await message.reply_text(
        "<b>🔑 Userbot Login</b>\n\n"
        "Apna Telegram <b>phone number</b> bhejein.\n"
        "Format: <code>+919876543210</code>\n\n"
        "❌ Cancel: /cancel",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command("logout") & filters.private)
async def cmd_logout(client, message: Message):
    user_id = message.from_user.id

    # Stop running userbot if any
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
        await message.reply_text(
            "<b>✅ Successfully logout ho gaye!</b>\n\n"
            "Dobara login ke liye: /login",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            "<b>⚠️ Aap pehle se logged out hain.</b>",
            parse_mode=enums.ParseMode.HTML
        )


@Client.on_message(filters.command("session") & filters.private)
async def cmd_session(client, message: Message):
    user_id = message.from_user.id
    session = await database.get_userbot_session(user_id)

    if not session:
        return await message.reply_text(
            "<b>❌ Koi active session nahi hai.</b>\n\n"
            "/login se apna account connect karein.",
            parse_mode=enums.ParseMode.HTML
        )

    from SilentXForward.forward import active_userbots
    ub = active_userbots.get(user_id)
    status = "🟢 Active" if (ub and ub.is_connected) else "🔴 Inactive (restart bot)"

    await message.reply_text(
        f"<b>📋 Session Info</b>\n\n"
        f"👤 Status: {status}\n"
        f"📱 Phone: <code>{session.get('phone', 'N/A')}</code>\n"
        f"🕐 Login: {session.get('created_at', 'N/A')}\n\n"
        f"Logout: /logout",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command("cancel") & filters.private)
async def cmd_cancel(client, message: Message):
    user_id = message.from_user.id
    if user_id in login_states:
        # Disconnect temp client if exists
        tc = login_states[user_id].get("temp_client")
        if tc:
            try:
                await tc.disconnect()
            except Exception:
                pass
        del login_states[user_id]
        await message.reply_text("<b>❌ Login process cancel kar diya.</b>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text("<b>⚠️ Koi active login process nahi hai.</b>", parse_mode=enums.ParseMode.HTML)


# ==================== LOGIN STEP HANDLER (OTP / PASSWORD) ====================

@Client.on_message(
    filters.private & filters.text &
    ~filters.command(["login", "logout", "session", "cancel", "start", "help", "about",
                      "set", "remove_target", "remove_source", "list", "clear"])
)
async def login_step_handler(client, message: Message):
    user_id = message.from_user.id

    if user_id not in login_states:
        return  # Not in login flow, ignore

    state = login_states[user_id]
    step = state.get("step")

    # ── Step 1: Phone number ──────────────────────────────────────────────────
    if step == "phone":
        phone = message.text.strip()
        msg = await message.reply_text("⏳ OTP bhej raha hoon...", parse_mode=enums.ParseMode.HTML)

        import config as cfg
        temp_client = Client(
            f"temp_{user_id}",
            api_id=cfg.API_ID,
            api_hash=cfg.API_HASH,
            in_memory=True,
        )
        try:
            await temp_client.connect()
            sent = await temp_client.send_code(phone)

            state["step"] = "otp"
            state["phone"] = phone
            state["phone_code_hash"] = sent.phone_code_hash
            state["temp_client"] = temp_client
            login_states[user_id] = state

            await msg.edit(
                "<b>📩 OTP bhej diya gaya!</b>\n\n"
                "Apne Telegram par aaya <b>OTP</b> yahan bhejein.\n"
                "Format: <code>12345</code>\n\n"
                "❌ Cancel: /cancel",
                parse_mode=enums.ParseMode.HTML
            )
        except PhoneNumberInvalid:
            await temp_client.disconnect()
            del login_states[user_id]
            await msg.edit(
                "<b>❌ Invalid phone number!</b>\n"
                "Sahi format: <code>+919876543210</code>",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await temp_client.disconnect()
            del login_states[user_id]
            await msg.edit(
                f"<b>❌ Error:</b> <code>{e}</code>\n\nDobara /login try karein.",
                parse_mode=enums.ParseMode.HTML
            )

    # ── Step 2: OTP ──────────────────────────────────────────────────────────
    elif step == "otp":
        otp = message.text.strip().replace(" ", "")
        temp_client = state.get("temp_client")
        phone = state["phone"]
        phone_code_hash = state["phone_code_hash"]

        try:
            await temp_client.sign_in(phone, phone_code_hash, otp)
            session_string = await temp_client.export_session_string()
            await temp_client.disconnect()

            await database.save_userbot_session(user_id, session_string, phone)
            del login_states[user_id]

            # Start the userbot immediately
            from SilentXForward.forward import start_single_userbot
            await start_single_userbot(user_id, session_string)

            await message.reply_text(
                "<b>✅ Login Successful!</b>\n\n"
                "🤖 Aapka userbot start ho gaya!\n"
                "Ab aap <b>private channels</b> bhi source/target set kar sakte hain.\n\n"
                "📋 Status: /session\n"
                "🚪 Logout: /logout",
                parse_mode=enums.ParseMode.HTML
            )

        except PhoneCodeInvalid:
            await message.reply_text(
                "<b>❌ Galat OTP!</b> Dobara sahi OTP bhejein.",
                parse_mode=enums.ParseMode.HTML
            )
        except PhoneCodeExpired:
            await temp_client.disconnect()
            del login_states[user_id]
            await message.reply_text(
                "<b>⏰ OTP expire ho gaya!</b> Dobara /login karein.",
                parse_mode=enums.ParseMode.HTML
            )
        except SessionPasswordNeeded:
            state["step"] = "password"
            login_states[user_id] = state
            await message.reply_text(
                "<b>🔐 2-Step Verification enabled hai!</b>\n\n"
                "Apna <b>password</b> bhejein:\n\n"
                "❌ Cancel: /cancel",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_states[user_id]
            await message.reply_text(
                f"<b>❌ Error:</b> <code>{e}</code>\n\nDobara /login try karein.",
                parse_mode=enums.ParseMode.HTML
            )

    # ── Step 3: 2FA Password ──────────────────────────────────────────────────
    elif step == "password":
        password = message.text.strip()
        temp_client = state.get("temp_client")
        phone = state["phone"]

        try:
            await temp_client.check_password(password)
            session_string = await temp_client.export_session_string()
            await temp_client.disconnect()

            await database.save_userbot_session(user_id, session_string, phone)
            del login_states[user_id]

            from SilentXForward.forward import start_single_userbot
            await start_single_userbot(user_id, session_string)

            await message.reply_text(
                "<b>✅ Login Successful! (2FA)</b>\n\n"
                "🤖 Aapka userbot start ho gaya!\n\n"
                "📋 Status: /session\n"
                "🚪 Logout: /logout",
                parse_mode=enums.ParseMode.HTML
            )
        except PasswordHashInvalid:
            await message.reply_text(
                "<b>❌ Galat password!</b> Dobara sahi password bhejein.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_states[user_id]
            await message.reply_text(
                f"<b>❌ Error:</b> <code>{e}</code>\n\nDobara /login try karein.",
                parse_mode=enums.ParseMode.HTML
            )
