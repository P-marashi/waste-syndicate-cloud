import os
from pathlib import Path

from ..registry import registry

# =============================================================================
# Bot
# =============================================================================

registry.BOT_TOKEN = os.environ["BOT_TOKEN"]
registry.API_BASE = f"https://botapi.rubika.ir/v3/{registry.BOT_TOKEN}"

registry.POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "3"))
registry.DEBUG = os.getenv("SYNDICATE_DEBUG", "1") == "1"

# =============================================================================
# Files
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

registry.SAVE_FILE = Path(
    os.getenv("SYNDICATE_SAVE", BASE_DIR / "waste_syndicate_save.json")
)

registry.TEXTS_DIR = Path(os.getenv("SYNDICATE_TEXTS_DIR", BASE_DIR / "texts"))

registry.OFFSET_FILE = BASE_DIR / "offset.json"

# =============================================================================
# Database
# =============================================================================

registry.USE_MONGO = os.getenv("USE_MONGO", "1") == "1"
registry.MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
registry.MONGO_DB = os.getenv("MONGO_DB", "waste_syndicate")

# Ephemeral state only (chat_states, short-lived caches) — never
# player progress. See storage/redis_client.py.
registry.USE_REDIS = os.getenv("USE_REDIS", "1") == "1"
registry.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# =============================================================================
# Game Configuration
# =============================================================================

registry.SKIP_PENDING_ON_START = True

registry.SEASON_LENGTH_DAYS = int(os.getenv("SEASON_LENGTH_DAYS", "21"))
registry.DAILY_EVENT_HOUR = int(os.getenv("DAILY_EVENT_HOUR", "7"))

# =============================================================================
# Alliance
# =============================================================================

registry.ALLIANCE_MAX = 8
registry.ALLIANCE_TAX_RATE = 0.06
registry.ALLIANCE_BONUS_RATE = 0.04
registry.ALLIANCE_DISTRIBUTE_RATE = 0.25

registry.SHIELD_DURATION = 12 * 3600

# =============================================================================
# Market
# =============================================================================

registry.SYSTEM_DAILY_RESTOCK = {
    "scrap": 25,
    "plastic": 20,
    "glass": 12,
    "battery": 3,
    "copper": 6,
}

registry.SYSTEM_STOCK_CAP = {
    "scrap": 75,
    "plastic": 60,
    "glass": 36,
    "battery": 9,
    "copper": 18,
}

# =============================================================================
# Limits
# =============================================================================

registry.MAX_ACTION_LOG = 60
registry.MAX_PRIVATE_MESSAGES = 500
registry.MAX_ADMIN_LOG = 300
registry.ADMIN_PLAYERS_PAGE_SIZE = 8

# =============================================================================
# Admin
# =============================================================================

registry.ADMIN_IDS = {
    admin_id.strip()
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip()
}

# =============================================================================
# Group
# =============================================================================

registry.GAME_GROUP_ID = os.getenv("GAME_GROUP_ID", "").strip()

registry.GROUP_RADIO_ENABLED = os.getenv("GROUP_RADIO_ENABLED", "1") == "1"

registry.GROUP_RADIO_MIN_INTERVAL = int(
    os.getenv("GROUP_RADIO_MIN_INTERVAL", str(2 * 3600))
)

registry.GROUP_BOSS_REPORT_INTERVAL = int(
    os.getenv("GROUP_BOSS_REPORT_INTERVAL", str(30 * 60))
)
