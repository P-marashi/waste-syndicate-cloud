from typing import Any

META_ID = "global"

# What's actually allowed to live in `meta` now. The big list fields
# (market_orders, private_messages, ...) have their own collections —
# see id_list_repository.py / log_repository.py.
SCALAR_KEYS = (
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


class MetaRepository:
    def __init__(self, db):
        self._db = db

    @property
    def collection(self):
        return self._db["meta"]

    def get(self) -> dict[str, Any]:
        doc = self.collection.find_one({"_id": META_ID})
        if not doc:
            return {}
        doc = dict(doc)
        doc.pop("_id", None)
        return doc

    def save(self, scalars: dict[str, Any]) -> None:
        payload = {key: scalars[key] for key in SCALAR_KEYS if key in scalars}
        self.collection.replace_one(
            {"_id": META_ID},
            {"_id": META_ID, **payload},
            upsert=True,
        )

    def increment(self, key: str, start: int = 1, amount: int = 1) -> int:
        """Counter helper matching the old `oid = game.get(key, 1);
        game[key] = oid + 1` pattern — returns the value *before*
        incrementing.

        NOTE: not yet atomic (read-then-write, two round trips). That's
        fine while a single process owns the game loop, same as today.
        If multiple workers ever write concurrently, switch this to a
        single `find_one_and_update` with `$inc` — at that point every id
        allocation must go through here instead of touching `meta`
        directly, which Phase 2 gets us to anyway.
        """
        doc = self.collection.find_one({"_id": META_ID}) or {}
        current = doc.get(key, start)
        self.collection.update_one(
            {"_id": META_ID},
            {"$set": {key: current + amount}},
            upsert=True,
        )
        return current
