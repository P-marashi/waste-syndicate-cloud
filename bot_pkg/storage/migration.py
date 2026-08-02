from typing import Any

from ..registry import registry
from .factories import default_game, default_season, generate_ref_code, new_player


def migrate_game(g: dict[str, Any]) -> dict[str, Any]:
    base = default_game()
    base.update(g or {})

    base["version"] = 4

    base.setdefault("players", {})
    base.setdefault("alliances", {})

    base.setdefault("market_orders", [])
    base.setdefault("next_order_id", 1)

    base.setdefault("barter_orders", [])
    base.setdefault("next_barter_id", 1)

    base.setdefault("resource_rentals", [])
    base.setdefault("next_rental_id", 1)

    # Migrated out to Redis (ChatStateRepository) — drop any leftover
    # copy from an older save/meta doc instead of carrying it forward.
    base.pop("chat_states", None)

    base.setdefault(
        "season",
        default_season(1),
    )

    base.setdefault("world_event_active", None)
    base.setdefault("last_daily_event", None)

    base.setdefault("world_boss", None)
    base.setdefault("last_boss_spawn", None)

    base.setdefault("news_feed", [])

    base.setdefault("last_group_radio_at", None)
    base.setdefault("last_group_boss_report_at", None)
    base.setdefault("last_group_rank1", None)

    base.setdefault("group_radio_log", [])

    base.setdefault("last_system_restock", None)
    base.setdefault("system_stock_log", [])

    base.setdefault(
        "market_supply",
        {r: 0 for r in registry.RESOURCES},
    )

    base.setdefault("private_messages", [])
    base.setdefault("next_private_message_id", 1)

    base.setdefault("admin_logs", [])
    base.setdefault("next_admin_log_id", 1)

    for r in registry.RESOURCES:
        base["market_supply"].setdefault(r, 0)

    for cid, p in list(base["players"].items()):
        fresh = new_player(
            p.get("name") or "",
            cid,
        )

        fresh.update(p)

        fresh.setdefault(
            "registered",
            bool(fresh.get("name")),
        )

        fresh.setdefault("resources", {})

        for r, v in new_player("", cid)["resources"].items():
            fresh["resources"].setdefault(r, v)

        fresh.setdefault("inventory", {})
        fresh.setdefault("buildings", {})
        fresh.setdefault("upgrades_in_progress", [])

        fresh.setdefault("stats", {})

        for k, v in new_player("", cid)["stats"].items():
            fresh["stats"].setdefault(k, v)
            fresh.setdefault(
                "ref_code",
                generate_ref_code(cid),
            )

        fresh.setdefault("referral_used", False)
        fresh.setdefault("referrals_count", 0)

        fresh.setdefault("loot_caches", 0)

        fresh.setdefault("mission_day", None)
        fresh.setdefault("daily_missions", [])

        fresh.setdefault("boss_cd", None)

        fresh.setdefault("season_points_bonus", 0)

        fresh.setdefault(
            "career",
            {
                "seasons_played": 0,
                "best_rank": None,
                "best_score": 0,
            },
        )

        fresh.setdefault("action_log", [])

        fresh.setdefault("banned", False)
        fresh.setdefault("ban_reason", "")
        fresh.setdefault("banned_at", None)
        fresh.setdefault("banned_by", None)
        fresh.setdefault("admin_notes", [])

        base["players"][cid] = fresh

    for name, al in list(base["alliances"].items()):
        if isinstance(al, list):
            members = [x for x in al if isinstance(x, str)]

            base["alliances"][name] = {
                "name": name,
                "owner": members[0] if members else "",
                "members": members,
                "open": True,
                "applicants": [],
                "vault": 0,
                "total_shared": 0,
                "level": 1,
                "group_raid_session": None,
                "group_raid_cd": None,
                "created_at": registry.iso(registry.now()),
                "log": [],
            }

        else:
            al.setdefault("name", name)

            al.setdefault(
                "owner",
                (al.get("members") or [""])[0],
            )

            al.setdefault("members", [])
            al.setdefault("open", True)
            al.setdefault("applicants", [])
            al.setdefault("vault", 0)
            al.setdefault("total_shared", 0)
            al.setdefault("level", 1)

            al.setdefault(
                "group_raid_session",
                None,
            )

            al.setdefault(
                "group_raid_cd",
                None,
            )

            al.setdefault("log", [])
            al.setdefault("log", [])

    return base
