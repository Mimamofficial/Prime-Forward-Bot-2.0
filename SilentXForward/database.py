import config
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(config.MONGO_URI)
db = mongo_client[config.DB_NAME]

channel_mappings = db['channel_mappings']
userbot_sessions = db['userbot_sessions']
user_settings    = db['user_settings']    # delay, on/off, endtext, filters
admins_col       = db['admins']
banned_col       = db['banned_users']
stats_col        = db['forward_stats']


# ==================== CHANNEL MAPPINGS ====================

async def get_user_mappings(user_id):
    cursor = channel_mappings.find({"user_id": user_id})
    return await cursor.to_list(length=None)

async def get_mapping_by_source(user_id, source_id):
    return await channel_mappings.find_one({"user_id": user_id, "source_id": source_id})

async def add_target_to_source(user_id, source_id, target_id, source_title, target_title):
    existing = await channel_mappings.find_one({"user_id": user_id, "source_id": source_id})
    if existing:
        if target_id not in existing.get('target_ids', []):
            await channel_mappings.update_one(
                {"user_id": user_id, "source_id": source_id},
                {"$push": {"target_ids": target_id}, "$set": {"source_title": source_title}}
            )
            return "added"
        return "exists"
    else:
        await channel_mappings.insert_one({
            "user_id": user_id, "source_id": source_id,
            "target_ids": [target_id], "source_title": source_title
        })
        return "created"

async def remove_target_from_source(user_id, source_id, target_id):
    result = await channel_mappings.update_one(
        {"user_id": user_id, "source_id": source_id, "target_ids": {"$exists": True}},
        {"$pull": {"target_ids": target_id}}
    )
    if result.modified_count > 0:
        mapping = await channel_mappings.find_one({"user_id": user_id, "source_id": source_id})
        if not mapping or not mapping.get('target_ids'):
            await channel_mappings.delete_one({"user_id": user_id, "source_id": source_id})
        return "removed"
    return "not_found"

async def remove_source(user_id, source_id):
    result = await channel_mappings.delete_one({"user_id": user_id, "source_id": source_id})
    return result.deleted_count > 0

async def get_all_targets_for_source(source_id):
    cursor = channel_mappings.find({"source_id": source_id})
    mappings = await cursor.to_list(length=None)
    return [{"user_id": m['user_id'], "target_ids": m.get('target_ids', [])} for m in mappings]

async def clear_all_mappings(user_id):
    result = await channel_mappings.delete_many({"user_id": user_id})
    return result.deleted_count


# ==================== USERBOT SESSIONS ====================

async def save_userbot_session(user_id: int, session_string: str, phone: str):
    from datetime import datetime
    await userbot_sessions.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "session_string": session_string,
                  "phone": phone, "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}},
        upsert=True
    )

async def get_userbot_session(user_id: int):
    return await userbot_sessions.find_one({"user_id": user_id})

async def delete_userbot_session(user_id: int) -> bool:
    result = await userbot_sessions.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def get_all_userbot_sessions():
    cursor = userbot_sessions.find({})
    return await cursor.to_list(length=None)


# ==================== USER SETTINGS ====================

async def _get_settings(user_id: int) -> dict:
    doc = await user_settings.find_one({"user_id": user_id})
    return doc or {}

async def _update_settings(user_id: int, data: dict):
    await user_settings.update_one({"user_id": user_id}, {"$set": data}, upsert=True)

# ── Forwarding ON/OFF ──
async def set_forwarding(user_id: int, enabled: bool):
    await _update_settings(user_id, {"forwarding_enabled": enabled})

async def is_forwarding_enabled(user_id: int) -> bool:
    doc = await _get_settings(user_id)
    return doc.get("forwarding_enabled", True)  # default ON

# ── Delay ──
async def set_delay(user_id: int, seconds: float):
    await _update_settings(user_id, {"delay": seconds})

async def get_delay(user_id: int) -> float:
    doc = await _get_settings(user_id)
    return doc.get("delay", 0.1)  # default 0.1s

# ── Keyword Filters ──
async def add_filter(user_id: int, word: str) -> bool:
    doc = await _get_settings(user_id)
    filters_list = doc.get("filters", [])
    word = word.lower().strip()
    if word in filters_list:
        return False
    filters_list.append(word)
    await _update_settings(user_id, {"filters": filters_list})
    return True

async def remove_filter(user_id: int, word: str) -> bool:
    doc = await _get_settings(user_id)
    filters_list = doc.get("filters", [])
    word = word.lower().strip()
    if word not in filters_list:
        return False
    filters_list.remove(word)
    await _update_settings(user_id, {"filters": filters_list})
    return True

async def get_filters(user_id: int) -> list:
    doc = await _get_settings(user_id)
    return doc.get("filters", [])

# ── End Text (Footer) ──
async def set_endtext(user_id: int, text: str):
    await _update_settings(user_id, {"endtext": text})

async def remove_endtext(user_id: int):
    await user_settings.update_one({"user_id": user_id}, {"$unset": {"endtext": ""}}, upsert=True)

async def get_endtext(user_id: int) -> str | None:
    doc = await _get_settings(user_id)
    return doc.get("endtext", None)

# ── All settings for a user (used in /status) ──
async def get_all_settings(user_id: int) -> dict:
    return await _get_settings(user_id)


# ==================== ADMIN SYSTEM ====================

async def add_admin(owner_id: int, target_user_id: int):
    await admins_col.update_one(
        {"owner_id": owner_id, "admin_id": target_user_id},
        {"$set": {"owner_id": owner_id, "admin_id": target_user_id}},
        upsert=True
    )

async def remove_admin(owner_id: int, target_user_id: int) -> bool:
    result = await admins_col.delete_one({"owner_id": owner_id, "admin_id": target_user_id})
    return result.deleted_count > 0

async def get_admins(owner_id: int) -> list:
    cursor = admins_col.find({"owner_id": owner_id})
    docs = await cursor.to_list(length=None)
    return [d["admin_id"] for d in docs]

async def is_admin(owner_id: int, user_id: int) -> bool:
    if owner_id == user_id:
        return True
    doc = await admins_col.find_one({"owner_id": owner_id, "admin_id": user_id})
    return doc is not None

# ── Ban System ──
async def ban_user(owner_id: int, target_user_id: int):
    await banned_col.update_one(
        {"owner_id": owner_id, "banned_id": target_user_id},
        {"$set": {"owner_id": owner_id, "banned_id": target_user_id}},
        upsert=True
    )

async def unban_user(owner_id: int, target_user_id: int) -> bool:
    result = await banned_col.delete_one({"owner_id": owner_id, "banned_id": target_user_id})
    return result.deleted_count > 0

async def is_banned(owner_id: int, user_id: int) -> bool:
    doc = await banned_col.find_one({"owner_id": owner_id, "banned_id": user_id})
    return doc is not None


# ==================== STATS ====================

async def increment_forward_count(user_id: int, count: int = 1):
    await stats_col.update_one(
        {"user_id": user_id},
        {"$inc": {"total_forwarded": count}},
        upsert=True
    )

async def get_forward_count(user_id: int) -> int:
    doc = await stats_col.find_one({"user_id": user_id})
    return doc.get("total_forwarded", 0) if doc else 0

async def reset_forward_count(user_id: int):
    await stats_col.update_one({"user_id": user_id}, {"$set": {"total_forwarded": 0}}, upsert=True)
