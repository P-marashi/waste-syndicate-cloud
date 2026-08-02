"""One-off migration: split the monolithic `meta` document's list fields
into their own collections.

Before: db.meta == {
    "_id": "global",
    "market_orders": [...],       # grows forever
    "barter_orders": [...],
    "resource_rentals": [...],
    "private_messages": [...],
    "admin_logs": [...],
    "news_feed": [...],
    "group_radio_log": [...],
    "system_stock_log": [...],
    ...scalars...
}

After: db.meta only has scalars; each list above gets its own collection
with one document per item and real indexes.

Idempotent — safe to run more than once. It always re-derives the target
collections from whatever is currently embedded in `meta`, then removes
those fields from `meta` once copied over.

Usage:
    cd bot_pkg/..   # repo root, so `bot_pkg` is importable
    uv run python -m bot_pkg.storage.migrate_meta_collections
"""

from .collections import ID_LIST_KEYS, LOG_KEYS, build_repositories
from ..infra.db import get_db

ALL_LIST_KEYS = ID_LIST_KEYS + LOG_KEYS


def run() -> None:
    db = get_db()
    repos = build_repositories(db, ensure_indexes=True)

    meta_doc = db.meta.find_one({"_id": "global"}) or {}

    if not meta_doc:
        print("No `meta` document found — nothing to migrate.")
        return

    moved: dict[str, int] = {}

    for key in ALL_LIST_KEYS:
        items = meta_doc.get(key) or []
        if items:
            repos[key].replace_all(items)
        moved[key] = len(items)

    unset_fields = {key: "" for key in ALL_LIST_KEYS if key in meta_doc}

    if unset_fields:
        db.meta.update_one({"_id": "global"}, {"$unset": unset_fields})

    print("Migration complete:")
    for key, count in moved.items():
        print(f"  {key}: {count} documents moved -> collection '{key}'")
    print(f"  meta document fields removed: {sorted(unset_fields)}")


if __name__ == "__main__":
    run()
