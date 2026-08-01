from typing import Any

from .registry import registry
from .services import alliance_service


def get_alliance(name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    return registry.game.get("alliances", {}).get(name)


registry.get_alliance = get_alliance


def player_alliance(chat_id: str) -> dict[str, Any] | None:
    p = registry.game["players"].get(chat_id)
    return registry.get_alliance(p.get("alliance")) if p else None


registry.player_alliance = player_alliance


def alliance_mode_text(al: dict[str, Any]) -> str:
    return (
        registry.T("alliance.open") if al.get("open") else registry.T("alliance.closed")
    )


registry.alliance_mode_text = alliance_mode_text


def cartel_level(al: dict[str, Any] | None) -> int:
    if not al:
        return 1
    return alliance_service.cartel_level(al.get("level", 1), registry.MAX_CARTEL_LEVEL)


registry.cartel_level = cartel_level


def cartel_level_data(al: dict[str, Any] | None) -> dict[str, Any]:
    return alliance_service.cartel_level_data(
        registry.cartel_level(al), registry.CARTEL_LEVELS
    )


registry.cartel_level_data = cartel_level_data


def cartel_next_upgrade_cost(al: dict[str, Any]) -> int:
    lv = registry.cartel_level(al)
    return alliance_service.cartel_next_upgrade_cost(
        lv, registry.MAX_CARTEL_LEVEL, registry.CARTEL_LEVELS
    )


registry.cartel_next_upgrade_cost = cartel_next_upgrade_cost


def cartel_water_bonus(chat_id: str) -> float:
    al = registry.player_alliance(chat_id)
    return float(registry.cartel_level_data(al).get("water_bonus", 0.0)) if al else 0.0


registry.cartel_water_bonus = cartel_water_bonus


def cartel_score_bonus(chat_id: str) -> int:
    al = registry.player_alliance(chat_id)
    return int(registry.cartel_level_data(al).get("score_bonus", 0)) if al else 0


registry.cartel_score_bonus = cartel_score_bonus


def cartel_perks_text(al: dict[str, Any] | None) -> str:
    data = registry.cartel_level_data(al)
    lines = [
        f"• 💧 پاداش تولید آب اعضا: +{int(float(data.get('water_bonus', 0)) * 100)}٪",
        f"• 🏆 پاداش امتیاز سیزن برای هر عضو: +{int(data.get('score_bonus', 0))}",
    ]
    return "\n".join(lines)


registry.cartel_perks_text = cartel_perks_text


def alliance_log(
    al: dict[str, Any], action: str, data: dict[str, Any] | None = None
) -> None:
    al.setdefault("log", []).append(
        {"at": registry.iso(registry.now()), "action": action, "data": data or {}}
    )
    al["log"] = al["log"][-80:]


registry.alliance_log = alliance_log


def distribute_alliance_income(
    source_id: str, pool: int, reason: str
) -> tuple[int, int, str]:
    if pool <= 0:
        return (0, 0, "")
    al = registry.player_alliance(source_id)
    if not al:
        return (0, 0, "")
    pool = int(pool * registry.event_mod("alliance_pool", 1.0))
    members = [
        cid
        for cid in al.get("members", [])
        if cid in registry.game["players"] and cid != source_id
    ]
    each, actual_dist, vault_add = alliance_service.distribute_pool(
        pool, len(members), registry.ALLIANCE_DISTRIBUTE_RATE
    )
    if not members:
        al["vault"] = int(al.get("vault", 0)) + vault_add
        al["total_shared"] = int(al.get("total_shared", 0)) + pool
        return (0, vault_add, registry.T("alliance.no_share"))
    for cid in members:
        mp = registry.game["players"][cid]
        mp["water"] = int(mp.get("water", 0)) + each
        mp.setdefault("stats", {})["alliance_received"] = (
            mp.get("stats", {}).get("alliance_received", 0) + each
        )
        registry.log_action(
            cid,
            "alliance_dividend",
            {"from": source_id, "amount": each, "reason": reason},
        )
    al["vault"] = int(al.get("vault", 0)) + vault_add
    al["total_shared"] = int(al.get("total_shared", 0)) + pool
    source = registry.game["players"][source_id]
    source.setdefault("stats", {})["alliance_shared"] = (
        source.get("stats", {}).get("alliance_shared", 0) + pool
    )
    return (
        actual_dist,
        vault_add,
        registry.T(
            "alliance.share_note",
            pool=pool,
            distributed=actual_dist,
            vault_add=vault_add,
        ),
    )


registry.distribute_alliance_income = distribute_alliance_income


def award_water(
    chat_id: str, gross: int, reason: str, alliance_share: bool = True
) -> tuple[int, str]:
    p = registry.game["players"][chat_id]
    gross = max(0, int(gross))
    if gross <= 0:
        return (0, "")
    net = gross
    note = ""
    if alliance_share and p.get("alliance"):
        net, tax, bonus = alliance_service.split_water_tax(
            gross, registry.ALLIANCE_TAX_RATE, registry.ALLIANCE_BONUS_RATE
        )
        pool = tax + bonus
        _, _, note = registry.distribute_alliance_income(chat_id, pool, reason)
    p["water"] = int(p.get("water", 0)) + net
    p.setdefault("stats", {})["water_earned"] = (
        p.get("stats", {}).get("water_earned", 0) + net
    )
    registry.log_action(
        chat_id, "water_income", {"gross": gross, "net": net, "reason": reason}
    )
    return (net, note)


registry.award_water = award_water
