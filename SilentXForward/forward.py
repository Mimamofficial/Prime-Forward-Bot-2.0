import asyncio
import logging
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError, ChannelInvalid, ChannelPrivate, ChatAdminRequired
from SilentXForward import database
import config as cfg

# ================= CONFIG =================
BUFFER_DELAY    = 3      # Wait 3s after LAST message before forwarding
QUEUE_WORKERS   = 3
TARGET_CONCURRENCY = 3
MSG_DELAY       = 0.1
TARGET_DELAY    = 0.15
MAX_RETRIES     = 3
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

message_queue  = asyncio.Queue()
message_buffer = defaultdict(list)
buffer_tasks   = {}
buffer_timers  = {}   # ✅ NEW: tracks last message time per chat

# Dedup tracker
seen_message_ids: dict[int, set] = defaultdict(set)

_bot_client = None

# ==================== USERBOT REGISTRY ====================
active_userbots: dict[int, Client] = {}


def _is_duplicate(chat_id: int, message_id: int) -> bool:
    if message_id in seen_message_ids[chat_id]:
        return True
    seen_message_ids[chat_id].add(message_id)
    if len(seen_message_ids[chat_id]) > 500:
        seen_message_ids[chat_id] = set(list(seen_message_ids[chat_id])[-500:])
    return False


async def start_single_userbot(user_id: int, session_string: str) -> Client:
    old = active_userbots.get(user_id)
    if old:
        try:
            await old.stop()
        except Exception:
            pass

    ub = Client(
        name=f"ub_{user_id}",
        api_id=cfg.API_ID,
        api_hash=cfg.API_HASH,
        session_string=session_string,
        in_memory=True,
        no_updates=False,
    )
    await ub.start()
    active_userbots[user_id] = ub
    _register_userbot_handler(ub, user_id)

    me = await ub.get_me()
    logger.info(f"✅ Userbot started: user_id={user_id} → @{me.username} ({me.first_name})")
    return ub


def _register_userbot_handler(ub: Client, user_id: int):
    @ub.on_message(
        filters.channel &
        (filters.video | filters.document | filters.photo |
         filters.audio | filters.animation | filters.text |
         filters.sticker | filters.voice | filters.video_note |
         filters.poll | filters.location | filters.contact)
    )
    async def userbot_forward_content(client, message):
        try:
            cid = message.chat.id
            if _is_duplicate(cid, message.id):
                return

            # ✅ FIX: Sirf message add karo — task cancel mat karo
            message_buffer[cid].append(message)

            # Agar task already chal raha hai toh naya mat banao
            old = buffer_tasks.get(cid)
            if old and not old.done():
                return  # existing task hi process karega

            # Naya task sirf tab banao jab koi task nahi hai
            buffer_tasks[cid] = asyncio.create_task(
                process_buffered_messages(cid, source_client=client)
            )
        except Exception:
            logger.exception(f"Userbot handler error for user {user_id}")

    logger.info(f"✅ Userbot handler registered for user_id={user_id}")


async def restore_all_userbots():
    sessions = await database.get_all_userbot_sessions()
    logger.info(f"Restoring {len(sessions)} userbot session(s)...")
    for doc in sessions:
        uid = doc.get("user_id")
        ss  = doc.get("session_string")
        if not uid or not ss:
            continue
        try:
            await start_single_userbot(uid, ss)
        except Exception as e:
            logger.error(f"Failed to restore userbot for user {uid}: {e}")
    logger.info(f"✅ Userbots restored: {len(active_userbots)}")


async def stop_all_userbots():
    for uid, ub in list(active_userbots.items()):
        try:
            await ub.stop()
        except Exception as e:
            logger.warning(f"Error stopping userbot {uid}: {e}")
    active_userbots.clear()


# ================= FLOOD HANDLER =================
async def handle_flood(func, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return await func(**kwargs)
        except FloodWait as e:
            logger.warning(f"FloodWait: sleeping {e.value}s")
            await asyncio.sleep(e.value + 1)
        except (ChannelInvalid, ChannelPrivate, ChatAdminRequired):
            # ✅ Retry se koi fayda nahi — seedha raise karo
            raise
        except RPCError as e:
            logger.error(f"RPCError: {e}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.exception(f"Unexpected error in RPC call: {e}")
            await asyncio.sleep(2 ** attempt)
    raise Exception("Max retries exceeded in handle_flood")


# ================= SINGLE FORWARD =================
async def forward_single_message(client, message, chat_id, sender_client=None, caption_extra: str = ""):
    try:
        writer = sender_client if sender_client else client

        extra_caption = None
        if caption_extra:
            existing = message.caption or message.text or ""
            extra_caption = f"{existing}\n\n{caption_extra}".strip() if existing else caption_extra

        # 🔍 TEMPORARY DEBUG — cover ki actual value log karo
        if message.video:
            logger.info(
                f"DEBUG VIDEO msg_id={message.id} | "
                f"cover={getattr(message.video, 'cover', 'ATTR_NOT_FOUND')} | "
                f"thumbs={message.video.thumbs}"
            )

        # ✅ COVER FIX: agar video ka custom cover set hai, send_cached_media use karo
        # copy_message cover field carry forward nahi karta.
        # send_cached_media DreamXBotz style mein cover directly support karta hai —
        # koi download/upload nahi, FILE_REFERENCE_EXPIRED ka koi chakkar nahi.
        # Agar cover nahi hai ya send_cached_media fail ho jaaye — normal copy_message pe fallback.
        cover = getattr(message.video, "cover", None) if message.video else None
        if cover:
            try:
                await handle_flood(
                    writer.send_cached_media,
                    chat_id=chat_id,
                    file_id=message.video.file_id,
                    cover=cover,
                    caption=extra_caption if extra_caption else message.caption,
                    protect_content=False,
                )
                return True
            except Exception:
                logger.warning(
                    f"send_cached_media with cover failed for msg_id={message.id}, "
                    f"falling back to copy_message"
                )
                # Fallback — neeche copy_message chalega

        if extra_caption:
            await handle_flood(
                writer.copy_message,
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
                caption=extra_caption,
            )
        else:
            await handle_flood(
                writer.copy_message,
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
            )
        return True

    except (ChannelInvalid, ChannelPrivate) as e:
        # ✅ FIX: Channel invalid/private — auto remove from ALL users' mappings
        logger.warning(f"Channel invalid/private: {chat_id} — auto removing from DB. Error: {e}")
        try:
            await database.remove_invalid_target(chat_id)
        except Exception as db_err:
            logger.error(f"DB cleanup failed for {chat_id}: {db_err}")
        return False

    except ChatAdminRequired as e:
        # Bot admin nahi — log karo, retry mat karo
        logger.warning(f"Bot not admin in {chat_id}: {e}")
        return False

    except Exception:
        logger.exception(f"Forward failed msg_id={getattr(message, 'id', None)} -> {chat_id}")
        if sender_client and sender_client != client:
            try:
                await handle_flood(
                    client.copy_message,
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.id,
                )
                return True
            except Exception:
                logger.exception(f"Bot fallback also failed -> {chat_id}")
        return False


# ================= BUFFER FORWARD =================
async def forward_buffered_messages(client, messages, chat_id, sender_client=None,
                                     msg_delay: float = MSG_DELAY, caption_extra: str = ""):
    success = 0
    for msg in sorted(messages, key=lambda m: m.id):
        try:
            ok = await forward_single_message(client, msg, chat_id,
                                              sender_client=sender_client,
                                              caption_extra=caption_extra)
            if ok:
                success += 1
        except Exception:
            logger.exception(f"Error forwarding buffered msg -> {chat_id}")
        await asyncio.sleep(msg_delay)
    return success


# ================= QUEUE WORKER =================
async def process_queue(client):
    from SilentXForward.logger import log_forward_success, log_forward_failed

    sem = asyncio.Semaphore(TARGET_CONCURRENCY)

    async def forward_target(chat_id, payload, ftype, sender_client, msg_delay, caption_extra):
        async with sem:
            if ftype == "buffered":
                return await forward_buffered_messages(
                    client, payload, chat_id,
                    sender_client=sender_client,
                    msg_delay=msg_delay,
                    caption_extra=caption_extra
                )
            return await forward_single_message(
                client, payload, chat_id,
                sender_client=sender_client,
                caption_extra=caption_extra
            )

    while True:
        try:
            payload, targets, ftype, retry_count, sender_client, source_info = await message_queue.get()

            user_id       = source_info.get("user_id")
            msg_delay     = source_info.get("delay", MSG_DELAY)
            caption_extra = source_info.get("endtext", "") or ""
            failed        = []
            succeeded     = []

            tasks = [
                forward_target(tid, payload, ftype, sender_client, msg_delay, caption_extra)
                for tid in targets
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            msg_count    = len(payload) if isinstance(payload, list) else 1
            source_id    = source_info.get("id", 0)
            source_title = source_info.get("title", str(source_id))

            for tid, res in zip(targets, results):
                if isinstance(res, Exception):
                    logger.error(f"Exception forwarding to {tid}: {res}")
                    failed.append((tid, str(res)))
                elif res is False or res == 0:
                    # False = channel invalid ya already handled — retry nahi
                    pass
                else:
                    succeeded.append(tid)

            if succeeded and user_id:
                try:
                    await database.increment_forward_count(user_id, len(succeeded) * msg_count)
                except Exception:
                    pass

            for tid in succeeded:
                try:
                    await log_forward_success(client, source_title, source_id, tid, msg_count)
                except Exception:
                    pass

            if failed:
                failed_tids = [f[0] for f in failed]
                if retry_count < MAX_RETRIES:
                    await message_queue.put((payload, failed_tids, ftype, retry_count + 1,
                                            sender_client, source_info))
                else:
                    for tid, err in failed:
                        try:
                            await log_forward_failed(client, source_id, tid, msg_count, err)
                        except Exception:
                            pass

            message_queue.task_done()
            await asyncio.sleep(TARGET_DELAY)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected error in queue worker — continuing")
            await asyncio.sleep(1)


# ================= WATCHDOG =================
async def worker_watchdog(client):
    while True:
        try:
            await asyncio.sleep(10)
            tasks = getattr(client, "_queue_tasks", {})
            for key, t in list(tasks.items()):
                if t.done():
                    exc = t.exception() if not t.cancelled() else None
                    logger.warning(f"Worker {key} died (exc={exc}), restarting...")
                    tasks[key] = asyncio.create_task(process_queue(client))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Watchdog error")


# ================= START / STOP =================
async def start_processor(client):
    tasks = {}
    for i in range(QUEUE_WORKERS):
        tasks[f"worker_{i}"] = asyncio.create_task(process_queue(client))
    tasks["watchdog"] = asyncio.create_task(worker_watchdog(client))
    logger.info(f"{QUEUE_WORKERS} queue workers + watchdog started")
    return tasks

async def start_forwarder(client):
    global _bot_client
    _bot_client = client
    if getattr(client, "_queue_tasks", None):
        return
    await restore_all_userbots()
    client._queue_tasks = await start_processor(client)

async def stop_forwarder(client, timeout: float = 5.0):
    tasks = getattr(client, "_queue_tasks", {}) or {}
    for t in tasks.values():
        t.cancel()
    try:
        await asyncio.wait_for(message_queue.join(), timeout=timeout)
    except Exception:
        pass
    await stop_all_userbots()
    client._queue_tasks = {}


# ================= BUFFER PROCESSOR =================
async def process_buffered_messages(source_chat_id, source_client=None):
    """
    ✅ DEBOUNCE FIX:
    Jab tak naye messages aa rahe hain — wait karo.
    Jab BUFFER_DELAY seconds tak koi naya message na aaye
    tabhi saare collected messages forward karo.
    Isse bulk messages mein koi bhi skip nahi hoga.
    """
    try:
        while True:
            await asyncio.sleep(BUFFER_DELAY)
            # Check: last message kitne time pehle aaya?
            last_time = buffer_timers.get(source_chat_id, 0)
            now = asyncio.get_event_loop().time()
            if now - last_time < BUFFER_DELAY:
                # Abhi bhi messages aa rahe hain — aur wait karo
                continue
            # Kaafi der se koi message nahi aaya — ab forward karo
            break

        messages = message_buffer.pop(source_chat_id, None)
        buffer_timers.pop(source_chat_id, None)

        if not messages:
            return

        # Deduplicate by message ID
        seen = set()
        unique_messages = []
        for m in messages:
            if m.id not in seen:
                seen.add(m.id)
                unique_messages.append(m)
        messages = unique_messages

        logger.info(f"Processing {len(messages)} buffered msgs from {source_chat_id}")

        source_title = str(source_chat_id)
        try:
            if source_client:
                chat = await source_client.get_chat(source_chat_id)
                source_title = chat.title or source_title
        except Exception:
            pass

        mappings = await database.get_all_targets_for_source(source_chat_id)
        for mapping in mappings:
            targets = mapping.get("target_ids", [])
            user_id = mapping.get("user_id")
            if not targets:
                continue

            if user_id and not await database.is_forwarding_enabled(user_id):
                logger.info(f"Forwarding OFF for user {user_id}, skipping")
                continue

            user_filters = await database.get_filters(user_id) if user_id else []
            if user_filters:
                filtered_messages = []
                for msg in messages:
                    text = (msg.text or msg.caption or "").lower()
                    if any(w in text for w in user_filters):
                        filtered_messages.append(msg)
                if not filtered_messages:
                    logger.info(f"All messages filtered out for user {user_id}")
                    continue
                messages_to_send = filtered_messages
            else:
                messages_to_send = messages

            msg_delay = await database.get_delay(user_id) if user_id else MSG_DELAY
            endtext   = await database.get_endtext(user_id) if user_id else None

            sender = source_client
            if user_id and user_id in active_userbots:
                ub = active_userbots[user_id]
                if ub.is_connected:
                    sender = ub

            source_info = {
                "id": source_chat_id,
                "title": source_title,
                "user_id": user_id,
                "delay": msg_delay,
                "endtext": endtext or "",
            }

            await message_queue.put((messages_to_send.copy(), targets, "buffered", 0, sender, source_info))
            logger.info(f"Queued {len(messages_to_send)} msgs from {source_chat_id} -> {len(targets)} targets")

    except asyncio.CancelledError:
        # Messages buffer mein safe hain — lost nahi honge
        logger.debug(f"Buffer task cancelled for {source_chat_id}")
        raise
    except Exception:
        logger.exception("Unexpected error in buffer processor")
        message_buffer.pop(source_chat_id, None)
        buffer_timers.pop(source_chat_id, None)
    finally:
        buffer_tasks.pop(source_chat_id, None)


def _handle_incoming_message(cid: int, message, source_client):
    """
    ✅ DEBOUNCE HELPER:
    Har naye message pe:
    1. Buffer mein add karo
    2. Timer update karo (last message time)
    3. Agar task already chal raha hai — rehne do (cancel mat karo!)
    4. Agar task nahi hai ya khatam ho gaya — naya banao
    """
    message_buffer[cid].append(message)
    # Timer update — last message time record karo
    buffer_timers[cid] = asyncio.get_event_loop().time()

    existing_task = buffer_tasks.get(cid)
    if existing_task and not existing_task.done():
        # Task chal raha hai — woh khud debounce loop mein wait karega
        return

    # Naya task banao
    buffer_tasks[cid] = asyncio.create_task(
        process_buffered_messages(cid, source_client=source_client)
    )


# ================= BOT MESSAGE LISTENER =================
@Client.on_message(
    filters.channel &
    (filters.video | filters.document | filters.photo |
     filters.audio | filters.animation | filters.text |
     filters.sticker | filters.voice | filters.video_note |
     filters.poll | filters.location | filters.contact)
)
async def forward_content(client, message):
    try:
        cid = message.chat.id
        if _is_duplicate(cid, message.id):
            return
        _handle_incoming_message(cid, message, source_client=client)
    except Exception:
        logger.exception("Bot handler error")
