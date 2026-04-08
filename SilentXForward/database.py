import config
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(config.MONGO_URI)
db = mongo_client[config.DB_NAME]

channel_mappings = db['channel_mappings']
userbot_sessions = db['userbot_sessions']  # ← NEW: userbot sessions collection

# ==================== CHANNEL MAPPINGS (unchanged) ====================

async def get_user_mappings(user_id):
    cursor = channel_mappings.find({"user_id": user_id})
    return await cursor.to_list(length=None)

async def get_mapping_by_source(user_id, source_id):
    return await channel_mappings.find_one({
        "user_id": user_id,
        "source_id": source_id
    })

async def add_target_to_source(user_id, source_id, target_id, source_title, target_title):
    existing = await channel_mappings.find_one({
        "user_id": user_id,
        "source_id": source_id
    })
    
    if existing:
        if target_id not in existing.get('target_ids', []):
            await channel_mappings.update_one(
                {"user_id": user_id, "source_id": source_id},
                {
                    "$push": {"target_ids": target_id},
                    "$set": {"source_title": source_title}
                }
            )
            return "added"
        return "exists"
    else:
        await channel_mappings.insert_one({
            "user_id": user_id,
            "source_id": source_id,
            "target_ids": [target_id],
            "source_title": source_title
        })
        return "created"

async def remove_target_from_source(user_id, source_id, target_id):
    result = await channel_mappings.update_one(
        {"user_id": user_id, "source_id": source_id, "target_ids": {"$exists": True}},
        {"$pull": {"target_ids": target_id}}
    )
    
    if result.modified_count > 0:
        mapping = await channel_mappings.find_one({"user_id": user_id, "source_id": source_id})
        if not mapping or not mapping.get('target_ids') or len(mapping.get('target_ids', [])) == 0:
            await channel_mappings.delete_one({"user_id": user_id, "source_id": source_id})
        return "removed"
    return "not_found"

async def remove_source(user_id, source_id):
    result = await channel_mappings.delete_one({
        "user_id": user_id,
        "source_id": source_id
    })
    return result.deleted_count > 0

async def get_all_targets_for_source(source_id):
    cursor = channel_mappings.find({"source_id": source_id})
    mappings = await cursor.to_list(length=None)
    
    result = []
    for mapping in mappings:
        result.append({
            "user_id": mapping['user_id'],
            "target_ids": mapping.get('target_ids', [])
        })
    return result

async def clear_all_mappings(user_id):
    result = await channel_mappings.delete_many({"user_id": user_id})
    return result.deleted_count


# ==================== USERBOT SESSIONS (NEW) ====================

async def save_userbot_session(user_id: int, session_string: str, phone: str):
    """Save or update userbot session in MongoDB."""
    from datetime import datetime
    await userbot_sessions.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "session_string": session_string,
            "phone": phone,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }},
        upsert=True
    )

async def get_userbot_session(user_id: int):
    """Load userbot session for a user. Returns None if not found."""
    return await userbot_sessions.find_one({"user_id": user_id})

async def delete_userbot_session(user_id: int) -> bool:
    """Delete userbot session. Returns True if deleted."""
    result = await userbot_sessions.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def get_all_userbot_sessions():
    """Load all saved userbot sessions (used at bot startup to restore)."""
    cursor = userbot_sessions.find({})
    return await cursor.to_list(length=None)
