import os

API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "PrimeForward)

WEB_SERVER = os.environ.get("WEB_SERVER", "True").lower() in ("true", "1", "t")
PORT = int(os.environ.get("PORT", "8080"))
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", "300"))

TG_WORKERS = int(os.environ.get("TG_WORKERS", "4"))

# Your Koyeb/Heroku App Url
# Example : https://yourappurl.koyeb.app/
APP_URL = os.environ.get("APP_URL", None)

# Log Channel ID — Yahan saare events log honge
# Example: -1001234567890
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0")) or None

# Owner ID — Sirf yeh user admin commands use kar sakta hai
# Example: 123456789
OWNER_ID = int(os.environ.get("OWNER_ID", "0")) or None

# Force Subscribe Channels
# Multiple channels comma separated: "-1001234567890,-1009876543210"
# Format: "channel_id:invite_link" ya sirf "channel_id" (agar public hai)
# Example: "-1001234567890:https://t.me/yourchannel,-1009876543210:https://t.me/+invitelink"
_fsub_raw = os.environ.get("FSUB_CHANNELS", "")
FSUB_CHANNELS = []
if _fsub_raw.strip():
    for entry in _fsub_raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            parts = entry.split(":", 1)
            FSUB_CHANNELS.append({
                "id": int(parts[0].strip()),
                "link": parts[1].strip()
            })
        elif entry:
            FSUB_CHANNELS.append({
                "id": int(entry),
                "link": None
            })

# FSub Banner Image — URL ya Telegram file_id dalo
# Example: "https://imgbb.com/yourimage.jpg"  ya  "AgACAgIxxxxx..."
# Blank chhod do agar image nahi lagani: FSUB_BANNER = ""
FSUB_BANNER = os.environ.get("FSUB_BANNER", "https://files.catbox.moe/uybezy.jpg")
