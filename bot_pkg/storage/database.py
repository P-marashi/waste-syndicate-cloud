from ..registry import registry

_mongo_client = None
_db = None


def get_db():
    global _mongo_client, _db

    if _db is not None:
        return _db

    from pymongo import MongoClient

    _mongo_client = MongoClient(
        registry.MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    _db = _mongo_client[registry.MONGO_DB]

    _db.players.create_index("name")
    _db.players.create_index("banned")
    _db.players.create_index("alliance")

    return _db


META_SCALAR_KEYS = (
    "version",
    "next_order_id",
    "next_barter_id",
    "next_rental_id",
    "next_private_message_id",
    "next_admin_log_id",
    "market_supply",
    "last_system_restock",
    "world_event_active",
    "last_daily_event",
    "world_boss",
    "last_boss_spawn",
    "last_group_radio_at",
    "last_group_boss_report_at",
    "last_group_rank1",
    "season",
    "chat_states",
    "next_offset_id",
)

META_LIST_KEYS = (
    "market_orders",
    "barter_orders",
    "resource_rentals",
    "private_messages",
    "admin_logs",
    "news_feed",
    "group_radio_log",
    "system_stock_log",
)
