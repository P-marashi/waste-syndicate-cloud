import json
from typing import Any

from pymongo import UpdateOne

from ..registry import registry
from .database import META_LIST_KEYS, META_SCALAR_KEYS, get_db
from .factories import default_game
from .migration import migrate_game


def _save_game_mongo() -> None:
    db = get_db()
    game = registry.game

    ops = [
        UpdateOne(
            {"_id": str(cid)},
            {"$set": {**p, "_id": str(cid)}},
            upsert=True,
        )
        for cid, p in game.get("players", {}).items()
    ]

    if ops:
        db.players.bulk_write(
            ops,
            ordered=False,
        )

    ops = [
        UpdateOne(
            {"_id": str(name)},
            {"$set": {**al, "_id": str(name)}},
            upsert=True,
        )
        for name, al in game.get("alliances", {}).items()
    ]

    if ops:
        db.alliances.bulk_write(
            ops,
            ordered=False,
        )

    meta: dict[str, Any] = {
        "_id": "global",
    }

    for key in META_SCALAR_KEYS:
        if key in game:
            meta[key] = game[key]

    for key in META_LIST_KEYS:
        meta[key] = game.get(key, [])

    db.meta.replace_one(
        {"_id": "global"},
        meta,
        upsert=True,
    )


def _load_game_mongo() -> dict[str, Any]:
    db = get_db()

    meta = db.meta.find_one({"_id": "global"})

    if not meta:
        return {}

    game: dict[str, Any] = {}

    meta.pop("_id", None)
    game.update(meta)

    game["players"] = {str(doc.pop("_id")): doc for doc in db.players.find()}

    game["alliances"] = {str(doc.pop("_id")): doc for doc in db.alliances.find()}

    return game


def save_game() -> None:
    try:
        if registry.USE_MONGO:
            _save_game_mongo()
        else:
            _save_game_json()

    except Exception as e:
        print(
            registry.T(
                "errors.save_failed",
                error=e,
            )
        )

        try:
            _save_game_json()
            print("[SAVE] fallback → JSON ok")

        except Exception as e2:
            print(f"[SAVE] JSON fallback failed: {e2}")


def _save_game_json() -> None:
    tmp = registry.SAVE_FILE.with_suffix(".tmp")

    with tmp.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            registry.game,
            f,
            ensure_ascii=False,
            indent=2,
        )

    tmp.replace(registry.SAVE_FILE)


def load_game() -> None:
    loaded: dict[str, Any] | None = None

    if registry.USE_MONGO:
        try:
            get_db().command("ping")

            raw = _load_game_mongo()

            if raw.get("players") is not None or raw.get("version"):
                loaded = raw
                print("✅ Loaded from MongoDB")

            elif registry.SAVE_FILE.exists():
                print("🔄 Mongo empty → migrating from JSON ...")

                with registry.SAVE_FILE.open(
                    "r",
                    encoding="utf-8",
                ) as f:
                    loaded = json.load(f)

        except Exception as e:
            print(f"[LOAD Mongo] {e} → trying JSON")

    if loaded is None and registry.SAVE_FILE.exists():
        with registry.SAVE_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:
            loaded = json.load(f)

        print("✅ Loaded from JSON file")

    registry.game = migrate_game(loaded) if loaded else default_game()

    print("🔧 Migrating building bonuses for existing players...")

    for cid in list(registry.game["players"].keys()):
        if registry.game["players"][cid].get("registered"):
            registry.migrate_player_building_bonuses(cid)

    print("✅ Building bonuses migrated.")

    save_game()
