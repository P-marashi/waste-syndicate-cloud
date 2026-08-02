import random
from datetime import timedelta
from typing import Any

from .registry import registry
from .services import misc_service


def inventory_resources_text(p: dict[str, Any]) -> str:
    """نمایش منابع پایه"""
    lines = [
        f"🔩 اوراق: {p['resources'].get('scrap', 0):,}",
        f"🧪 پلاستیک: {p['resources'].get('plastic', 0):,}",
        f"🔮 شیشه: {p['resources'].get('glass', 0):,}",
        f"🔋 باتری: {p['resources'].get('battery', 0):,}",
        f"🪙 مس: {p['resources'].get('copper', 0):,}",
        f"💧 آب: {p.get('water', 0):,}",
    ]
    return "\n".join(lines)


registry.inventory_resources_text = inventory_resources_text


def inventory_equipment_text(p: dict[str, Any]) -> str:
    """نمایش تجهیزات ساخته شده"""
    items = []
    for k, qty in p.get("inventory", {}).items():
        if qty > 0 and k in registry.CRAFT_ITEMS:
            item = registry.CRAFT_ITEMS[k]
            effects = []
            if item.get("atk"):
                effects.append(f"⚔️{item['atk']}")
            if item.get("def"):
                effects.append(f"🛡️{item['def']}")
            items.append(
                f"{item['label']} × {qty} {'(' + ', '.join(effects) + ')' if effects else ''}"
            )
    if not items:
        return "هیچ تجهیزاتی نداری. از 🛠️ کارگاه بساز."
    return "\n".join(items)


registry.inventory_equipment_text = inventory_equipment_text


def inventory_special_text(p: dict[str, Any]) -> str:
    """نمایش آیتم‌های ویژه و لوت‌ها"""
    parts = []
    # Legendary items
    for k, qty in p.get("inventory", {}).items():
        if qty > 0 and k in registry.LEGENDARY_ITEMS:
            parts.append(f"✨ {registry.LEGENDARY_ITEMS[k]['label']} × {qty}")
    # Loot caches
    caches = int(p.get("loot_caches", 0))
    if caches > 0:
        parts.append(f"🎁 صندوق شانسی × {caches}")
    if not parts:
        return "آیتم ویژه‌ای نداری."
    return "\n".join(parts)


registry.inventory_special_text = inventory_special_text


def handle_inventory(chat_id: str) -> None:
    """نمایش انبار با سه بخش مجزا"""
    p = registry.get_player(chat_id)

    text = f"""🎒 انبار
━━━━━━━━━━━━
📦 منابع
{registry.inventory_resources_text(p)}
━━━━━━━━━━━━
⚔️ تجهیزات
{registry.inventory_equipment_text(p)}
━━━━━━━━━━━━
⭐ آیتم‌های ویژه
{registry.inventory_special_text(p)}"""

    keypad_rows = [
        [registry.B("resources"), registry.B("equipment")],
        [registry.B("special_items")],
        [registry.B("main_menu")],
    ]
    registry.save_game()
    registry.send(chat_id, text, keypad=registry.make_keypad(keypad_rows))


registry.handle_inventory = handle_inventory


def handle_inventory_category(chat_id: str, category: str) -> None:
    """نمایش دسته‌بندی خاص از انبار"""
    p = registry.get_player(chat_id)

    if category == "resources":
        title = "📦 منابع"
        content = registry.inventory_resources_text(p)
    elif category == "equipment":
        title = "⚔️ تجهیزات"
        content = registry.inventory_equipment_text(p)
    elif category == "special_items":
        title = "⭐ آیتم‌های ویژه"
        content = registry.inventory_special_text(p)
    else:
        return registry.handle_inventory(chat_id)

    text = f"""{title}
━━━━━━━━━━━━
{content}"""

    keypad_rows = [
        [registry.B("inventory")],
        [registry.B("main_menu")],
    ]
    registry.send(chat_id, text, keypad=registry.make_keypad(keypad_rows))


registry.handle_inventory_category = handle_inventory_category


def handle_daily(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    if p.get("daily_last") == registry.today_key():
        tomorrow = (registry.now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        registry.send(
            chat_id,
            registry.T(
                "daily.already",
                time=registry.fmt_cd((tomorrow - registry.now()).total_seconds()),
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    yesterday = (registry.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    p["daily_streak"] = misc_service.next_daily_streak(
        p.get("daily_streak", 0), p.get("daily_last"), yesterday
    )
    p["daily_last"] = registry.today_key()
    streak = p["daily_streak"]
    reward = misc_service.compute_daily_reward(streak)
    water, scrap, plastic, battery = (
        reward["water"],
        reward["scrap"],
        reward["plastic"],
        reward["battery"],
    )
    p["water"] += water
    p["resources"]["scrap"] += scrap
    p["resources"]["plastic"] += plastic
    p["resources"]["battery"] += battery
    reward_text = registry.fmt_res_dict(
        {
            "water": water,
            "scrap": scrap,
            "plastic": plastic,
            **({"battery": battery} if battery else {}),
        }
    )
    registry.log_action(chat_id, "daily", {"reward": reward_text, "streak": streak})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("daily.claimed", reward=reward_text, streak=streak),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_daily = handle_daily


def handle_invite(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.send(
        chat_id,
        registry.T("invite.text", code=p.get("ref_code")),
        keypad=registry.make_keypad(
            [[registry.B("enter_referral")], [registry.B("main_menu")]]
        ),
    )


registry.handle_invite = handle_invite


def handle_enter_referral(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    if p.get("referral_used"):
        registry.send(
            chat_id, registry.T("invite.already"), keypad=registry.main_keypad(chat_id)
        )
        return
    registry.chat_state_repo.save(chat_id, {"state": "awaiting_referral_code"})
    registry.send(
        chat_id,
        registry.T("invite.prompt"),
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_enter_referral = handle_enter_referral


def handle_referral_code(chat_id: str, text: str) -> None:
    ok = registry.apply_referral(chat_id, text)
    registry.chat_state_repo.delete(chat_id)
    if ok:
        inviter_id = registry.game["players"][chat_id].get("referred_by")
        registry.send(
            chat_id,
            registry.T("invite.used", inviter=registry.player_name(inviter_id)),
            keypad=registry.main_keypad(chat_id),
        )
    else:
        registry.send(
            chat_id, registry.T("invite.bad"), keypad=registry.main_keypad(chat_id)
        )


registry.handle_referral_code = handle_referral_code


def handle_season(chat_id: str) -> None:
    rows = registry.ranked_players()
    rank = next((i for i, (cid, _) in enumerate(rows, start=1) if cid == chat_id), "—")
    s = registry.game.get("season", registry.default_season(1))
    br = registry.season_score_breakdown(chat_id)
    registry.send(
        chat_id,
        registry.T(
            "season.text",
            id=s.get("id", 1),
            start=registry.fmt_dt(s.get("start")),
            end=registry.fmt_dt(s.get("end")),
            left=registry.season_left_text(),
            score=br["total"],
            rank=rank,
            combat_score=br["combat"],
            eco_score=br["economy"],
            progress_score=br["progress"],
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_season = handle_season


def leaderboard_personal_note(chat_id: str, rows: list[tuple[str, int]]) -> str:
    total_players = len(rows)
    found = misc_service.find_leaderboard_rank(chat_id, rows)
    if not found:
        return registry.T("leaderboard.no_rank", total=total_players)
    my_rank, my_score = found
    if my_rank <= 10:
        return registry.T(
            "leaderboard.in_top", rank=my_rank, total=total_players, score=my_score
        )
    roasts = registry.T("leaderboard.roasts")
    if isinstance(roasts, list):
        roast = random.choice(roasts)
    else:
        roast = str(roasts)
    return registry.T(
        "leaderboard.out_of_top",
        rank=my_rank,
        total=total_players,
        score=my_score,
        roast=roast,
    )


registry.leaderboard_personal_note = leaderboard_personal_note


def previous_season_champion() -> dict[str, Any] | None:
    archives = registry.game.get("season", {}).get("archives", [])
    if not archives:
        return None
    last = archives[-1]
    winners = last.get("winners", [])
    if not winners:
        return None
    champ = winners[0]
    return {
        "chat_id": champ.get("chat_id"),
        "name": champ.get("name"),
        "score": champ.get("score"),
        "season_id": last.get("id"),
    }


registry.previous_season_champion = previous_season_champion


def handle_leaderboard(chat_id: str) -> None:
    rows = registry.ranked_players()
    medals = ["🥇", "🥈", "🥉"]
    champ = registry.previous_season_champion()
    champ_id = champ.get("chat_id") if champ else None
    lines = []
    for i, (cid, score) in enumerate(rows[:10]):
        p = registry.game["players"][cid]
        registry.recalc_power(p)
        crown = " 👑 قهرمان فصل قبل" if champ_id and cid == champ_id else ""
        lines.append(
            registry.T(
                "leaderboard.line",
                medal=medals[i] if i < 3 else f"{i + 1}.",
                name=registry.display_name(p.get("name")) + crown,
                level=p.get("level", 1),
                score=score,
                water=p.get("water", 0),
                attack=f"{p.get('total_attack', 0):,}",
                defense=f"{p.get('total_defense', 0):,}",
                power=f"{p.get('total_attack', 0) + p.get('total_defense', 0):,}",
                me=registry.T("leaderboard.me") if cid == chat_id else "",
            )
        )
    hof_line = ""
    if champ:
        hof_line = f"🏛️ تالار مشاهیر\n👑 قهرمان فصل {champ['season_id']}: {registry.display_name(champ['name'])} — {registry.fmt_num(champ['score'])} امتیاز\nاین لقب تا پایان همین فصل روی اسمش می\u200cمونه.\n\n"
    note = registry.leaderboard_personal_note(chat_id, rows)
    registry.send(
        chat_id,
        hof_line
        + registry.T(
            "leaderboard.text", lines="\n".join(lines) or "هنوز کسی نیست.", note=note
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_leaderboard = handle_leaderboard
