import random
from typing import Any

from ..registry import registry


def registered_player_ids(include_banned: bool = False) -> list[str]:
    return [
        cid
        for cid, p in registry.game.get("players", {}).items()
        if p.get("registered") and (include_banned or not p.get("banned"))
    ]


registry.registered_player_ids = registered_player_ids


def fmt_reward_dict(reward: dict[str, int]) -> str:
    parts = []
    for k, v in (reward or {}).items():
        if k == "xp":
            parts.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            parts.append(f"🎁 صندوق زنگ‌زده × {v}")
        else:
            parts.append(registry.fmt_res_amount(k, int(v)))
    return " + ".join(parts) if parts else "—"


registry.fmt_reward_dict = fmt_reward_dict


def award_mission_reward(p: dict[str, Any], reward: dict[str, int]) -> str:
    """Give a mission reward and return a clear receipt line for the player."""
    paid: list[str] = []
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            registry.add_xp(p, v)
            paid.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            p["loot_caches"] = int(p.get("loot_caches", 0)) + v
            paid.append(f"🎁 صندوق زنگ‌زده × {v}")
        else:
            registry.add_amount(p, k, v)
            paid.append(registry.fmt_res_amount(k, v))
    return " + ".join(paid) if paid else "—"


registry.award_mission_reward = award_mission_reward


def mission_line_text(m: dict[str, Any]) -> str:
    progress = int(m.get("progress", 0))
    goal = int(m.get("goal", 1))
    done = progress >= goal
    if m.get("claimed"):
        icon = "✅"
        status = "دریافت شده ✅"
        reward_label = "پاداش دریافتی"
    elif done:
        icon = "🎁"
        status = "آماده دریافت 🎁"
        reward_label = "پاداش آماده"
    else:
        icon = "⬜"
        status = "در حال انجام"
        reward_label = "پاداش"
    return registry.T(
        "missions.line",
        ok=icon,
        title=m.get("title"),
        progress=progress,
        goal=goal,
        reward=registry.fmt_reward_dict(m.get("reward", {})),
        status=status,
        reward_label=reward_label,
    )


registry.mission_line_text = mission_line_text


def profile_daily_missions_text(chat_id: str) -> str:
    missions = registry.ensure_daily_missions(chat_id)
    lines = []
    for m in missions:
        lines.append(registry.mission_line_text(m))
    if registry.daily_missions_claimed(chat_id):
        note = registry.T("missions.claimed")
    elif registry.daily_missions_done(chat_id):
        note = registry.T("missions.ready_in_profile")
    else:
        note = registry.T("missions.profile_hint")
    return registry.T("missions.profile_block", lines="\n".join(lines), note=note)


registry.profile_daily_missions_text = profile_daily_missions_text


def ensure_daily_missions(chat_id: str) -> list[dict[str, Any]]:
    p = registry.get_player(chat_id)
    if p.get("mission_day") != registry.today_key() or not isinstance(
        p.get("daily_missions"), list
    ):
        chosen = random.sample(registry.DAILY_MISSION_TEMPLATES, 3)
        p["mission_day"] = registry.today_key()
        p["daily_final_claimed"] = False
        p["daily_missions"] = [
            {
                "key": m["key"],
                "title": m["title"],
                "goal": int(m["goal"]),
                "progress": 0,
                "reward": dict(m.get("reward", {})),
                "claimed": False,
            }
            for m in chosen
        ]
    templates = {m.get("key"): m for m in registry.DAILY_MISSION_TEMPLATES}
    for m in p.get("daily_missions", []):
        if not isinstance(m, dict):
            continue
        tpl = templates.get(m.get("key"), {})
        if not m.get("title") and tpl.get("title"):
            m["title"] = tpl["title"]
        if not m.get("reward") and tpl.get("reward"):
            m["reward"] = dict(tpl.get("reward", {}))
        m.setdefault("claimed", False)
        m["progress"] = min(
            int(m.get("progress", 0)), int(m.get("goal", tpl.get("goal", 1)))
        )
    return p["daily_missions"]


registry.ensure_daily_missions = ensure_daily_missions


def inc_mission(chat_id: str, key: str, amount: int = 1) -> None:
    missions = registry.ensure_daily_missions(chat_id)
    for m in missions:
        if m.get("key") == key and (not m.get("claimed")):
            m["progress"] = min(
                int(m.get("goal", 1)), int(m.get("progress", 0)) + amount
            )


registry.inc_mission = inc_mission


def daily_missions_done(chat_id: str) -> bool:
    missions = registry.ensure_daily_missions(chat_id)
    return all(int(m.get("progress", 0)) >= int(m.get("goal", 1)) for m in missions)


registry.daily_missions_done = daily_missions_done


def daily_missions_claimed(chat_id: str) -> bool:
    missions = registry.ensure_daily_missions(chat_id)
    return bool(missions) and all(bool(m.get("claimed")) for m in missions)


registry.daily_missions_claimed = daily_missions_claimed


def handle_daily_missions(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    missions = registry.ensure_daily_missions(chat_id)
    receipts: list[str] = []
    for m in missions:
        ready = int(m.get("progress", 0)) >= int(m.get("goal", 1))
        if ready and (not m.get("claimed")):
            paid = registry.award_mission_reward(p, m.get("reward", {}))
            m["claimed"] = True
            m["claimed_at"] = registry.iso(registry.now())
            receipts.append(
                registry.T(
                    "missions.receipt_line",
                    title=m.get("title", "مأموریت"),
                    reward=paid,
                )
            )
    final_note = ""
    if all(bool(m.get("claimed")) for m in missions) and (
        not p.get("daily_final_claimed")
    ):
        p["water"] = int(p.get("water", 0)) + 150
        p["loot_caches"] = int(p.get("loot_caches", 0)) + 1
        p["daily_final_claimed"] = True
        p.setdefault("stats", {})["missions_completed"] = (
            int(p.get("stats", {}).get("missions_completed", 0)) + 1
        )
        registry.add_news(
            f"📜 {registry.player_name(chat_id)} مأموریت‌های روزانه را کامل کرد و پاداش نهایی گرفت."
        )
        final_note = registry.T("missions.final_reward")
    lines = [registry.mission_line_text(m) for m in missions]
    if receipts:
        note = registry.T("missions.receipt", lines="\n".join(receipts))
    elif all(bool(m.get("claimed")) for m in missions):
        note = registry.T("missions.claimed")
    else:
        ready_count = sum(
            1
            for m in missions
            if int(m.get("progress", 0)) >= int(m.get("goal", 1))
            and (not m.get("claimed"))
        )
        note = (
            registry.T("missions.ready_hint", count=ready_count)
            if ready_count
            else registry.T("missions.in_progress")
        )
    if final_note:
        note += "\n" + final_note
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("missions.text", lines="\n".join(lines), note=note),
        keypad=registry.make_keypad(
            [
                [registry.B("daily_missions")],
                [registry.B("open_cache")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_daily_missions = handle_daily_missions
