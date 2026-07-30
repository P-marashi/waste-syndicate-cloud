from typing import Any

from bot_pkg.registry import registry
from bot_pkg.utils.datetime import iso, now


def log_action(
    chat_id: str,
    action: str,
    data: dict[str, Any] | None = None,
) -> None:
    p = registry.game["players"].get(chat_id)

    if not p:
        return

    p.setdefault(
        "action_log",
        [],
    ).append(
        {
            "at": iso(now()),
            "action": action,
            "data": data or {},
        }
    )

    p["action_log"] = p["action_log"][-registry.MAX_ACTION_LOG :]


def admin_audit(
    admin_id: str,
    action: str,
    data: dict[str, Any] | None = None,
) -> None:
    aid = int(
        registry.game.get(
            "next_admin_log_id",
            1,
        )
    )

    registry.game["next_admin_log_id"] = aid + 1

    registry.game.setdefault(
        "admin_logs",
        [],
    ).append(
        {
            "id": aid,
            "at": iso(now()),
            "admin": admin_id,
            "action": action,
            "data": data or {},
        }
    )

    registry.game["admin_logs"] = registry.game["admin_logs"][-registry.MAX_ADMIN_LOG :]
