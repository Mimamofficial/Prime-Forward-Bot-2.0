import asyncio
import logging
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError
from SilentXForward import database
import config as cfg

# ================= CONFIG =================
BUFFER_DELAY = 2
QUEUE_WORKERS = 3
TARGET_CONCURRENCY = 3
MSG_DELAY = 0.1
TARGET_DELAY = 0.15
MAX_RETRIES = 3
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

message_queue = asyncio.Queue()
message_buffer = defaultdict(list)
buffer_tasks = {}

# Bot client reference (set in start_forwarder)
_bot_client = None

# ==================== USERBOT REGISTRY ====================
active_userbots: dict[int, Client] = {}


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
         filters.audio | filters.animation | filters.text)
    )
    async def userbot_forward_content(client, message):
        try:
            cid = message.chat.id
            message_buffer[cid].append(message)

            old = buffer_tasks.get(cid)
            if old and not old.done():
                try:
                    old.cancel()
                    await asyncio.sleep(0)
                except Exception:
                    pass

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
        ss = doc.get("session_string")
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
        except RPCError as e:
            logger.error(f"RPCError: {e}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.exception(f"Unexpected error in RPC call: {e}")
            await asyncio.sleep(2 ** attempt)
    raise Exception("Max retries exceeded in handle_flood")


# ================= SINGLE FORWARD =================
async def forward_single_message(client, message, chat_id, sender_client=None):
    try:
        writer = sender_client if sender_client else client
        await handle_flood(
            writer.copy_message,
            chat_id=chat_id,
            from_chat_id=message.chat.id,
            message_id=message.id,
        )
        return True
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
async def forward_buffered_messages(client, messages, chat_id, sender_client=None):
    success = 0
    for msg in sorted(messages, key=lambda m: m.id):
        try:
            ok = await forward_single_message(client, msg, chat_id, sender_client=sender_client)
            if ok:
                success += 1
        except Exception:
            logger.exception(f"Error forwarding buffered msg -> {chat_id}")
        await asyncio.sleep(MSG_DELAY)
    return success


# ================= QUEUE WORKER =================
async def process_queue(client):
    from SilentXForward.logger import log_forward_success, log_forward_failed

    sem = asyncio.Semaphore(TARGET_CONCURRENCY)

    async def forward_target(chat_id, payload, ftype, sender_client):
        async with sem:
            if ftype == "buffered":
                return await forward_buffered_messages(client, payload, chat_id, sender_client=sender_client)
            return await forward_single_message(client, payload, chat_id, sender_client=sender_client)

    while True:
        try:
            payload, targets, ftype, retry_count, sender_client, source_info = await message_queue.get()
            failed = []
            succeeded = []

            tasks = [forward_target(tid, payload, ftype, sender_client) for tid in targets]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            msg_count = len(payload) if isinstance(payload, list) else 1
            source_id = source_info.get("id", 0)
            source_title = source_info.get("title", str(source_id))

            for tid, res in zip(targets, results):
                if isinstance(res, Exception):
                    logger.error(f"Exception forwarding to {tid}: {res}")
                    failed.append((tid, str(res)))
                elif res is False or res == 0:
                    failed.append((tid, "Forward returned False"))
                else:
                    succeeded.append(tid)

            # ✅ Log successes
            for tid in succeeded:
                try:
                    await log_forward_success(client, source_title, source_id, tid, msg_count)
                except Exception:
                    pass

            # ❌ Log failures (only on final retry)
            if failed:
                failed_tids = [f[0] for f in failed]
                if retry_count < MAX_RETRIES:
                    logger.info(f"Retrying {len(failed_tids)} targets (attempt {retry_count + 1}/{MAX_RETRIES})")
                    await message_queue.put((payload, failed_tids, ftype, retry_count + 1,
                                            sender_client, source_info))
                else:
                    logger.error(f"Giving up on {len(failed_tids)} targets: {failed_tids}")
                    for tid, err in failed:
                        try:
                            await log_forward_failed(client, source_id, tid, msg_count, err)
                        except Exception:
                            pass

            message_queue.task_done()
            await asyncio.sleep(TARGET_DELAY)

        except asyncio.CancelledError:
            logger.info("Queue worker cancelled")
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
        t = asyncio.create_task(process_queue(client))
        tasks[f"worker_{i}"] = t
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
        logger.info("Shutdown: queue join timeout or interrupted")
    await stop_all_userbots()
    client._queue_tasks = {}


# ================= BUFFER PROCESSOR =================
async def process_buffered_messages(source_chat_id, source_client=None):
    try:
        await asyncio.sleep(BUFFER_DELAY)

        messages = message_buffer.pop(source_chat_id, None)
        if not messages:
            return

        # Get source title for logging
        source_title = str(source_chat_id)
        try:
            if source_client:
                chat = await source_client.get_chat(source_chat_id)
                source_title = chat.title or source_title
        except Exception:
            pass

        source_info = {"id": source_chat_id, "title": source_title}

        mappings = await database.get_all_targets_for_source(source_chat_id)
        for mapping in mappings:
            targets = mapping.get("target_ids", [])
            user_id = mapping.get("user_id")

            if not targets:
                continue

            sender = source_client
            if user_id and user_id in active_userbots:
                ub = active_userbots[user_id]
                if ub.is_connected:
                    sender = ub

            await message_queue.put((messages.copy(), targets, "buffered", 0, sender, source_info))
            logger.info(f"Queued {len(messages)} msgs from {source_chat_id} -> {len(targets)} targets")

    except asyncio.CancelledError:
        logger.debug(f"Buffer task for {source_chat_id} cancelled")
        raise
    except Exception:
        logger.exception("Unexpected error in buffer processor")
        message_buffer.pop(source_chat_id, None)
    finally:
        buffer_tasks.pop(source_chat_id, None)


# ================= BOT MESSAGE LISTENER =================
@Client.on_message(
    filters.channel &
    (filters.video | filters.document | filters.photo |
     filters.audio | filters.sticker | filters.animation | filters.text)
)
async def forward_content(client, message):
    try:
        cid = message.chat.id
        message_buffer[cid].append(message)

        old = buffer_tasks.get(cid)
        if old and not old.done():
            try:
                old.cancel()
                await asyncio.sleep(0)
            except Exception:
                pass

        buffer_tasks[cid] = asyncio.create_task(
            process_buffered_messages(cid, source_client=client)
        )
    except Exception:
        logger.exception("Bot handler error")
