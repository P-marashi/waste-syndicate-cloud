import random
import time
from datetime import timedelta
from typing import Any

from ..registry import registry


def boss_power_estimate(p: dict[str, Any]) -> int:
    registry.recalc_power(p)
    return max(
        35,
        int(p.get("total_attack", 0))
        + int(int(p.get("total_defense", 0)) * 0.25)
        + int(p.get("level", 1)) * 35,
    )


registry.boss_power_estimate = boss_power_estimate


def boss_scaled_stats(template: dict[str, Any]) -> dict[str, int]:
    """
    باس باید با تعداد بازیکن‌ها بزرگ شود، اما غیرممکن نشود.
    هدف این فرمول:
    - با تعداد بازیکن بیشتر، خون باس زیاد شود.
    - برای گروه کوچک هم باس قابل‌زدن ولی سخت بماند.
    - با ۲۷ بازیکن، باس نیاز به مشارکت جدی داشته باشد، نه چند ضربه ساده.
    """
    ids = registry.registered_player_ids()
    player_count = max(1, len(ids))
    powers = [
        registry.boss_power_estimate(registry.game["players"][cid]) for cid in ids
    ]
    avg_power = int(sum(powers) / max(1, len(powers))) if powers else 90
    expected_hits_per_player = 3.8 + min(2.2, player_count / 18)
    difficulty = float(template.get("reward_mod", 1.0)) * random.uniform(1.12, 1.38)
    scaled_hp = int(avg_power * player_count * expected_hits_per_player * difficulty)
    floor_hp = int(16000 + player_count * 2600)
    ceiling_hp = int(max(floor_hp, avg_power * player_count * 8.5))
    hp = max(floor_hp, min(scaled_hp, ceiling_hp))
    atk = int(template.get("atk", 14) + min(28, player_count * 0.55) + avg_power / 180)
    return {
        "hp": hp,
        "atk": max(10, atk),
        "players": player_count,
        "avg_power": avg_power,
    }


registry.boss_scaled_stats = boss_scaled_stats


def active_boss() -> dict[str, Any] | None:
    boss = registry.game.get("world_boss")
    if not boss:
        return None
    if (
        registry.fromiso(boss.get("expires_at"), registry.now()) <= registry.now()
        or int(boss.get("hp", 0)) <= 0
    ):
        return None
    return boss


registry.active_boss = active_boss


def maybe_spawn_boss(force: bool = False) -> dict[str, Any] | None:
    boss = registry.active_boss()
    if boss:
        return boss
    week_start = registry.now() - timedelta(days=registry.now().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    bosses_this_week = 0
    last_spawn = registry.fromiso(registry.game.get("last_boss_spawn"))
    if last_spawn and last_spawn >= week_start:
        bosses_this_week = 1
    if not force:
        if bosses_this_week >= registry.MAX_BOSSES_PER_WEEK:
            return None
        last = registry.fromiso(
            registry.game.get("last_boss_spawn"), registry.now() - timedelta(days=10)
        )
        elapsed = (registry.now() - last).total_seconds()
        if elapsed < registry.BOSS_MIN_INTERVAL:
            return None
        time_factor = min(
            1.0,
            (elapsed - registry.BOSS_MIN_INTERVAL)
            / (registry.BOSS_MAX_INTERVAL - registry.BOSS_MIN_INTERVAL),
        )
        spawn_chance = 0.45 + time_factor * 0.48
        if registry.now().weekday() >= 5:
            spawn_chance += 0.15
        if random.random() > spawn_chance:
            return None
    tmpl = dict(random.choice(registry.BOSS_TEMPLATES))
    scaled = registry.boss_scaled_stats(tmpl)
    boss_id = f"boss-{int(time.time())}"
    boss = {
        "id": boss_id,
        "name": tmpl["name"],
        "hp": int(scaled["hp"]),
        "max_hp": int(scaled["hp"]),
        "atk": int(scaled["atk"]),
        "reward_mod": float(tmpl["reward_mod"]),
        "spawned_at": registry.iso(registry.now()),
        "expires_at": registry.iso(
            registry.now() + timedelta(seconds=registry.BOSS_DURATION)
        ),
        "participants": {},
        "scaled_for_players": int(scaled["players"]),
        "avg_player_power": int(scaled["avg_power"]),
    }
    registry.game["world_boss"] = boss
    registry.game["last_boss_spawn"] = registry.iso(registry.now())
    registry.add_news(
        registry.T(
            "boss.spawned",
            name=boss["name"],
            hp=registry.fmt_num(boss["max_hp"]),
            players=registry.fmt_num(boss["scaled_for_players"]),
            hours=registry.BOSS_DURATION // 3600,
        ),
        important=True,
    )
    registry.save_game()
    return boss


registry.maybe_spawn_boss = maybe_spawn_boss


def boss_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [[registry.B("boss_attack")], [registry.B("city_map"), registry.B("main_menu")]]
    )


registry.boss_keypad = boss_keypad


def handle_world_boss(chat_id: str) -> None:
    boss = registry.active_boss() or registry.maybe_spawn_boss(False)
    if not boss:
        last = registry.fromiso(
            registry.game.get("last_boss_spawn"),
            registry.now() - timedelta(seconds=registry.BOSS_SPAWN_EVERY),
        )
        wait = max(
            0, registry.BOSS_SPAWN_EVERY - int((registry.now() - last).total_seconds())
        )
        registry.send(
            chat_id,
            registry.T("boss.none", time=registry.fmt_cd(wait)),
            keypad=registry.main_keypad(chat_id),
        )
        return
    parts = boss.get("participants", {})
    top = sorted(parts.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True)[
        :5
    ]
    top_lines = (
        "\n".join(
            (
                f"{i}. {registry.player_name(cid)} — {registry.fmt_num(v.get('damage', 0))}"
                for i, (cid, v) in enumerate(top, 1)
            )
        )
        or "هنوز کسی نزده."
    )
    hp_pct = int(int(boss.get("hp", 0)) / max(1, int(boss.get("max_hp", 1))) * 100)
    text = registry.T(
        "boss.menu",
        name=boss["name"],
        hp=registry.fmt_num(boss["hp"]),
        max_hp=registry.fmt_num(boss["max_hp"]),
        pct=hp_pct,
        left=registry.fmt_cd(
            (
                registry.fromiso(boss.get("expires_at"), registry.now())
                - registry.now()
            ).total_seconds()
        ),
        top=top_lines,
        cd=registry.fmt_cd(registry.cd_remaining(registry.get_player(chat_id), "boss")),
        players=registry.fmt_num(
            boss.get("scaled_for_players", len(registry.registered_player_ids()))
        ),
        avg_power=registry.fmt_num(boss.get("avg_player_power", 0)),
    )
    meta = registry.build_meta_bold(text, [(text[:25], 25), "جان:", "زمان باقی‌مانده:"])
    registry.send(chat_id, text, keypad=registry.boss_keypad(), meta_data=meta)


registry.handle_world_boss = handle_world_boss


def finish_boss_if_dead(killer_id: str) -> bool:
    boss = registry.game.get("world_boss")
    if not boss or int(boss.get("hp", 0)) > 0:
        return False
    participants = boss.get("participants", {})
    if not participants:
        registry.game["world_boss"] = None
        return True
    total_damage = sum(int(v.get("damage", 0)) for v in participants.values())
    if total_damage <= 0:
        registry.game["world_boss"] = None
        return True
    sorted_parts = sorted(
        participants.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True
    )
    reward_lines = []
    big_hitters = 0
    for rank, (cid, info) in enumerate(sorted_parts, 1):
        if cid not in registry.game["players"]:
            continue
        p = registry.game["players"][cid]
        dmg = int(info.get("damage", 0))
        water = int((160 + dmg / 35) * float(boss.get("reward_mod", 1.0)))
        if dmg >= 2000:
            water += 450
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 2
            big_hitters += 1
            registry.send(
                cid,
                "🏆 ضربه سنگین! (+۴۵۰ آب + ۲ صندوق)",
                keypad=registry.main_keypad(cid),
            )
        if rank == 1:
            water += 320
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 3
        elif rank <= 3:
            water += 180
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 2
        damage_share = dmg / total_damage
        extra = int(800 * damage_share)
        water += extra
        p["water"] = int(p.get("water", 0)) + water
        p["resources"]["battery"] = p["resources"].get("battery", 0) + (
            3 if rank <= 3 else 1
        )
        p["resources"]["copper"] = p["resources"].get("copper", 0) + (
            6 if rank <= 3 else 2
        )
        registry.maybe_award_legendary(
            cid, "باس جهانی", chance=0.03 if rank <= 3 else 0.008
        )
        registry.send(
            cid,
            registry.T(
                "boss.reward",
                name=boss["name"],
                rank=rank,
                damage=registry.fmt_num(dmg),
                water=registry.fmt_num(water),
            ),
            keypad=registry.main_keypad(cid),
        )
        reward_lines.append(
            f"{rank}. {registry.player_name(cid)} — {registry.fmt_num(dmg)} dmg"
        )
    registry.add_news(
        registry.T(
            "boss.defeated",
            name=boss["name"],
            killer=registry.player_name(killer_id),
            top="\n".join(reward_lines[:8]),
        ),
        important=True,
    )
    registry.game["world_boss"] = None
    return True


registry.finish_boss_if_dead = finish_boss_if_dead


def handle_boss_attack(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    registry.recalc_power(p)
    boss = registry.active_boss() or registry.maybe_spawn_boss(False)
    if not boss:
        registry.send(
            chat_id,
            registry.T("boss.none", time=registry.fmt_cd(0)),
            keypad=registry.main_keypad(chat_id),
        )
        return
    if registry.cd_remaining(p, "boss") > 0:
        registry.send(
            chat_id,
            registry.T(
                "boss.cooldown", time=registry.fmt_cd(registry.cd_remaining(p, "boss"))
            ),
            keypad=registry.boss_keypad(),
        )
        return
    power = (
        int(p.get("total_attack", 0))
        + int(p.get("total_defense", 0)) * 0.25
        + int(p.get("level", 1)) * 35
    )
    damage = max(25, int(power * random.uniform(0.8, 1.25)))
    boss["hp"] = max(0, int(boss.get("hp", 0)) - damage)
    part = boss.setdefault("participants", {}).setdefault(
        chat_id, {"damage": 0, "hits": 0}
    )
    part["damage"] = int(part.get("damage", 0)) + damage
    part["hits"] = int(part.get("hits", 0)) + 1
    p.setdefault("stats", {})["boss_damage"] = (
        p.get("stats", {}).get("boss_damage", 0) + damage
    )
    p.setdefault("stats", {})["boss_hits"] = p.get("stats", {}).get("boss_hits", 0) + 1
    registry.inc_mission(chat_id, "boss_attack", 1)
    boss_hit = random.randint(0, int(boss.get("atk", 10)))
    p["hp"] = max(1, int(p.get("hp", 100)) - boss_hit)
    registry.set_cd(p, "boss", registry.BOSS_ATTACK_CD)
    defeated = registry.finish_boss_if_dead(chat_id)
    registry.save_game()
    if defeated:
        registry.send(
            chat_id,
            registry.T("boss.killshot", damage=registry.fmt_num(damage)),
            keypad=registry.main_keypad(chat_id),
        )
    else:
        registry.send(
            chat_id,
            registry.T(
                "boss.attack_result",
                name=boss["name"],
                damage=registry.fmt_num(damage),
                boss_hp=registry.fmt_num(boss["hp"]),
                hp=p.get("hp", 100),
                hit=boss_hit,
                cd=registry.fmt_cd(registry.BOSS_ATTACK_CD),
            ),
            keypad=registry.boss_keypad(),
        )


registry.handle_boss_attack = handle_boss_attack


def handle_city_map(chat_id: str) -> None:
    boss = registry.active_boss()
    p = registry.get_player(chat_id)

    boss_line = (
        registry.T(
            "map.boss_active", name=boss["name"], hp=registry.fmt_num(boss["hp"])
        )
        if boss
        else registry.T("map.boss_none")
    )
    cache_count = int(p.get("loot_caches", 0))

    text = f"""🗺️ نقشه شهر متروکه
━━━━━━━━━━━━
{boss_line}
🎁 صندوق‌های غارت: {cache_count} عدد
━━━━━━━━━━━━
📍 مناطق گشت‌زنی"""

    keypad_rows = [
        [registry.B("scavenge_alley"), registry.B("scavenge_suburb")],
        [registry.B("scavenge_center"), registry.B("scavenge_bunker")],
        [registry.B("world_boss"), registry.B("lucky_box")],
        [registry.B("city_news")],
        [registry.B("main_menu")],
    ]

    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad(keypad_rows),
    )


registry.handle_city_map = handle_city_map
