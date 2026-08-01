import json
from typing import Any

from ..registry import registry
from .collections import ID_LIST_KEYS, LOG_KEYS, build_repositories
from .database import get_db
from .factories import default_game
from .migration import migrate_game


def _save_game_mongo() -> None:
    """Persist `registry.game` via the repository layer.

    NOTE: this is a *transitional bridge*. It still reads the whole
    in-memory `game` dict and re-syncs each collection, same as the old
    code — but now each piece of data lands in its own collection with
    real indexes instead of one giant `meta` document. Once handlers call
    repository methods directly (Phase 2), this full-resync step goes
    away for that data and each action writes only what it touched.
    """
    db = get_db()
    game = registry.game
    repos = build_repositories(db)

    for cid, p in game.get("players", {}).items():
        repos["players"].save(cid, p)

    for name, al in game.get("alliances", {}).items():
        repos["alliances"].save(name, al)

    for key in ID_LIST_KEYS:
        repos[key].replace_all(game.get(key, []))

    for key in LOG_KEYS:
        repos[key].replace_all(game.get(key, []))

    repos["meta"].save(game)


def _load_game_mongo() -> dict[str, Any]:
    db = get_db()
    repos = build_repositories(db)

    meta = repos["meta"].get()

    if not meta:
        return {}

    game: dict[str, Any] = dict(meta)

    game["players"] = repos["players"].list_all()
    game["alliances"] = repos["alliances"].list_all()

    for key in ID_LIST_KEYS:
        game[key] = repos[key].list_all()

    for key in LOG_KEYS:
        game[key] = repos[key].list_all()

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
