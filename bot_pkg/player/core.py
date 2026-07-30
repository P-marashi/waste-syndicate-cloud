from typing import Any

from ..registry import registry


def get_player(chat_id: str, name: str = "") -> dict[str, Any]:
    if chat_id not in registry.game["players"]:
        registry.game["players"][chat_id] = registry.new_player(None, chat_id)

    p = registry.game["players"][chat_id]

    if name and not p.get("name"):
        p["name"] = name

    return p


def player_name(chat_id: str) -> str:
    p = registry.game["players"].get(chat_id)

    if p and p.get("name"):
        return p["name"]

    return str(chat_id)[-6:]


def find_player_by_name(
    name: str,
    candidates: list[str] | None = None,
) -> str | None:
    name_norm = (name or "").strip().lower()

    pool = candidates or list(registry.game["players"].keys())

    for cid in pool:
        if (
            registry.game["players"].get(cid, {}).get("name", "").strip().lower()
            == name_norm
        ):
            return cid

    for cid in pool:
        if (
            name_norm
            and name_norm
            in registry.game["players"].get(cid, {}).get("name", "").strip().lower()
        ):
            return cid

    return None
