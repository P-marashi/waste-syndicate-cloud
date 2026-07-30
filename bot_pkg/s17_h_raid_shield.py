import random
from datetime import timedelta
from typing import Any

from .registry import registry


def raid_target_button(name: str) -> str:
    return registry.T("raid.button", name=name)


registry.raid_target_button = raid_target_button


def raid_bucket_from_text(text: str) -> str | None:
    for key, cfg in registry.RAID_BUCKETS.items():
        if text == registry.B(cfg["button_key"]):
            return key
    return None


registry.raid_bucket_from_text = raid_bucket_from_text


def raid_target_score(p: dict[str, Any]) -> int:
    registry.recalc_power(p)
    return (
        int(p.get("water", 0))
        + int(p.get("total_defense", 0)) * 2
        + int(p.get("total_attack", 0)) * 2
        + int(p.get("level", 1)) * 120
    )


registry.raid_target_score = raid_target_score


def raid_candidates(
    chat_id: str, include_shielded: bool = False
) -> list[tuple[str, dict[str, Any]]]:
    rows = []
    for cid, rp in registry.game["players"].items():
        if cid == chat_id or not rp.get("registered"):
            continue
        if not include_shielded and registry.is_shielded(rp):
            continue
        registry.recalc_power(rp)
        rows.append((cid, rp))
    rows.sort(key=lambda x: registry.raid_target_score(x[1]))
    return rows


registry.raid_candidates = raid_candidates


def raid_bucket_targets(
    chat_id: str, bucket_key: str
) -> list[tuple[str, dict[str, Any]]]:
    candidates = registry.raid_candidates(chat_id)
    if len(candidates) <= 2:
        return candidates
    third = max(1, (len(candidates) + 2) // 3)
    if bucket_key == "weak":
        return candidates[:third]
    if bucket_key == "medium":
        return candidates[third : third * 2] or candidates
    if bucket_key == "strong":
        return candidates[third * 2 :] or candidates[-third:]
    return candidates


registry.raid_bucket_targets = raid_bucket_targets


def handle_attack_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    registry.recalc_power(p)
    if p.get("hp", 100) < 25:
        registry.send(
            chat_id, registry.T("raid.low_hp"), keypad=registry.main_keypad(chat_id)
        )
        return
    if registry.cd_remaining(p, "raid") > 0:
        registry.send(
            chat_id,
            registry.T(
                "raid.cooldown", time=registry.fmt_cd(registry.cd_remaining(p, "raid"))
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    if int(p.get("total_attack", 0)) <= 0:
        registry.send(
            chat_id,
            registry.T("raid.zero_attack"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    candidates = registry.raid_candidates(chat_id)
    if not candidates:
        registry.send(
            chat_id,
            registry.T("errors.no_rivals"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    bucket_lines = []
    rows = []
    for key, cfg in registry.RAID_BUCKETS.items():
        targets = registry.raid_bucket_targets(chat_id, key)
        button = registry.B(cfg["button_key"])
        bucket_lines.append(
            registry.T(
                "raid.bucket_line",
                button=button,
                title=cfg["title"],
                count=len(targets),
                loot=int(cfg["loot_mod"] * 100),
                risk="کم" if key == "weak" else "معمولی" if key == "medium" else "زیاد",
            )
        )
        rows.append([button])
    drone_count = int(p.get("inventory", {}).get("spy_drone", 0))
    direct_lines = []
    if drone_count > 0:
        direct_targets = sorted(
            candidates, key=lambda x: registry.raid_target_score(x[1]), reverse=True
        )[:12]
        for cid, rp in direct_targets:
            button = registry.raid_target_button(rp.get("name"))
            direct_lines.append(
                registry.T(
                    "raid.direct_line",
                    button=button,
                    name=registry.display_name(rp.get("name")),
                    level=rp.get("level", 1),
                    defense=f"{rp.get('total_defense', 0):,}",
                    water=f"{rp.get('water', 0):,}",
                )
            )
            rows.append([button])
        drone_hint = registry.T("raid.drone_available", count=drone_count)
    else:
        drone_hint = registry.T("raid.drone_hint")
        direct_lines.append(drone_hint)
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T(
            "raid.menu",
            attack=f"{p.get('total_attack', 0):,}",
            bucket_lines="\n".join(bucket_lines),
            direct_lines="\n".join(direct_lines),
            drone_count=drone_count,
        ),
        keypad=registry.make_keypad(rows),
    )


registry.handle_attack_menu = handle_attack_menu


def raid_target_from_text(text: str) -> str | None:
    if text.startswith("حمله دقیق:"):
        name = text.split(":", 1)[1].strip()
        return registry.find_player_by_name(name)
    if text.startswith("حمله:"):
        name = text.split(":", 1)[1].strip()
        return registry.find_player_by_name(name)
    return None


registry.raid_target_from_text = raid_target_from_text


def handle_random_raid(chat_id: str, bucket_key: str) -> None:
    targets = registry.raid_bucket_targets(chat_id, bucket_key)
    if not targets:
        registry.send(
            chat_id,
            registry.T(
                "raid.no_bucket_targets",
                title=registry.RAID_BUCKETS[bucket_key]["title"],
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    target_id, _ = random.choice(targets)
    registry.handle_raid(chat_id, target_id, bucket_key=bucket_key, precise=False)


registry.handle_random_raid = handle_random_raid


def handle_raid(
    chat_id: str, target_id: str, bucket_key: str | None = None, precise: bool = False
) -> None:
    p = registry.get_player(chat_id)
    t = registry.game["players"].get(target_id)
    if not t:
        registry.send(
            chat_id,
            registry.T("errors.target_not_found"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    if p.get("alliance") and t.get("alliance") == p.get("alliance"):
        registry.send(
            chat_id,
            "❌ نمی\u200cتوانی به اعضای اتحاد خودت حمله کنی.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    registry.recalc_power(p)
    registry.recalc_power(t)
    if p.get("hp", 100) < 25:
        registry.send(
            chat_id, registry.T("raid.low_hp"), keypad=registry.main_keypad(chat_id)
        )
        return
    if registry.cd_remaining(p, "raid") > 0:
        registry.send(
            chat_id,
            registry.T(
                "raid.cooldown", time=registry.fmt_cd(registry.cd_remaining(p, "raid"))
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    if registry.is_shielded(t):
        registry.send(
            chat_id,
            registry.T("raid.shielded", name=registry.display_name(t.get("name"))),
            keypad=registry.main_keypad(chat_id),
        )
        return
    if int(p.get("total_attack", 0)) <= 0:
        registry.send(
            chat_id,
            registry.T("raid.zero_attack"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    raid_notes = []
    if registry.is_shielded(p):
        p["shield_until"] = None
        raid_notes.append("⚠️ محافظت شکست.")
    drone_used = False
    if precise:
        if int(p.get("inventory", {}).get("spy_drone", 0)) <= 0:
            registry.send(
                chat_id,
                registry.T("raid.need_drone"),
                keypad=registry.main_keypad(chat_id),
            )
            return
        if t.get("level", 1) < 3 and abs(t.get("level", 1) - p.get("level", 1)) > 3:
            registry.send(
                chat_id,
                "❌ پهپاد فقط برای اهداف سطح ۳ به بالا یا نزدیک به سطح تو کار می\u200cکند.",
                keypad=registry.main_keypad(chat_id),
            )
            return
        p["inventory"]["spy_drone"] -= 1
        if p["inventory"].get("spy_drone", 0) <= 0:
            p["inventory"].pop("spy_drone", None)
        drone_used = True
        raid_notes.append("🚁 پهپاد جاسوسی مصرف شد؛ هدف دقیق قفل شد.")
    bucket_key = bucket_key or "medium"
    cfg = registry.RAID_BUCKETS.get(bucket_key, registry.RAID_BUCKETS["medium"])
    raid_type = (
        registry.T("raid.mode_direct")
        if precise
        else registry.T("raid.mode_random", title=cfg["title"])
    )
    p["stats"]["raids_done"] = p["stats"].get("raids_done", 0) + 1
    t["stats"]["raids_received"] = t["stats"].get("raids_received", 0) + 1
    registry.inc_mission(chat_id, "raid", 1)
    atk = int(p.get("total_attack", 0) * random.uniform(0.92, 1.28) * cfg["atk_mod"])
    atk = int(atk * (1 + p.get("level", 1) * 0.028))
    defense = int(t.get("total_defense", 0) * random.uniform(0.82, 1.18))
    defense = int(defense * (1 + max(0, t.get("level", 1) - 4) * 0.04))
    defense *= registry.event_mod("defense", 1.0)
    emp_mult = registry.consume_next_raid_emp(chat_id, p, raid_notes)
    if emp_mult < 1.0:
        defense = int(defense * emp_mult)
    if p.get("inventory", {}).get("emp_bomb", 0) > 0:
        p["inventory"]["emp_bomb"] -= 1
        if p["inventory"].get("emp_bomb", 0) <= 0:
            p["inventory"].pop("emp_bomb", None)
        defense = int(defense * 0.75)
        raid_notes.append("💣 بمب EMP مصرف شد؛ دفاع هدف ۲۵٪ ضعیف\u200cتر شد.")
    if (
        t.get("temp_defense_until")
        and registry.fromiso(t.get("temp_defense_until"), registry.now())
        > registry.now()
    ):
        defense = int(defense * 1.15)
    raid_note = "\n".join(raid_notes)
    cd = int(32 * 60 * registry.event_mod("raid_cd", 1.0))
    if atk > defense:
        loot_pct = 0.135 * cfg["loot_mod"] * registry.event_mod("raid_loot", 1.0)
        gross = min(t.get("water", 0), int(t.get("water", 0) * loot_pct))
        t["water"] = max(0, int(t.get("water", 0)) - gross)
        t["stats"]["water_lost"] = t["stats"].get("water_lost", 0) + gross
        net, note = registry.award_water(chat_id, gross, "raid", alliance_share=True)
        p["honor"] += int(cfg["honor_win"])
        t["honor"] -= 4
        leveled = registry.add_xp(p, int(cfg["xp"]))
        registry.set_cd(p, "raid", cd)
        registry.log_action(
            chat_id,
            "raid_win",
            {
                "target": target_id,
                "gross": gross,
                "net": net,
                "bucket": bucket_key,
                "precise": precise,
                "drone_used": drone_used,
            },
        )
        registry.log_action(
            target_id, "raid_lost", {"attacker": chat_id, "lost": gross}
        )
        registry.register_revenge_target(chat_id, target_id, gross)
        registry.complete_bounty_contracts(chat_id, target_id)
        registry.add_news(
            f"⚔️ {registry.player_name(chat_id)} به {registry.player_name(target_id)} حمله کرد و {gross:,} آب غارت کرد."
        )
        registry.send(
            target_id,
            registry.T(
                "raid.victim", attacker=registry.display_name(p.get("name")), lost=gross
            ),
            keypad=registry.main_keypad(target_id),
        )
        registry.send(
            chat_id,
            registry.T(
                "raid.win",
                raid_type=raid_type,
                target=registry.display_name(t.get("name")),
                atk=f"{int(atk):,}",
                defense=f"{int(defense):,}",
                gross=f"{gross:,}",
                net=f"{net:,}",
                raid_note=raid_note + "\n" if raid_note else "",
                share_note=note,
                honor=p["honor"],
                level_msg=registry.T("scavenge.level_up", level=p["level"])
                if leveled
                else "",
                cooldown=registry.fmt_cd(cd),
            ),
            keypad=registry.main_keypad(chat_id),
        )
    else:
        dmg = random.randint(10, 28)
        p["hp"] = max(1, p.get("hp", 100) - dmg)
        p["honor"] += int(cfg["honor_lose"])
        t["honor"] += 4
        registry.set_cd(p, "raid", cd)
        registry.log_action(
            chat_id,
            "raid_lose",
            {
                "target": target_id,
                "damage": dmg,
                "bucket": bucket_key,
                "precise": precise,
                "drone_used": drone_used,
            },
        )
        registry.send(
            chat_id,
            registry.T(
                "raid.lose",
                raid_type=raid_type,
                target=registry.display_name(t.get("name")),
                atk=f"{int(atk):,}",
                defense=f"{int(defense):,}",
                raid_note=raid_note + "\n" if raid_note else "",
                hp=p["hp"],
                honor=p["honor"],
                cooldown=registry.fmt_cd(cd),
            ),
            keypad=registry.main_keypad(chat_id),
        )
    registry.save_game()


registry.handle_raid = handle_raid


def handle_shield(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    sh = registry.shield_remaining(p)
    if sh > 0:
        registry.send(
            chat_id,
            registry.T("shield.active", time=registry.fmt_cd(sh)),
            keypad=registry.main_keypad(chat_id),
        )
        return
    cost = 150
    registry.send(
        chat_id,
        registry.T("shield.menu", cost=cost, water=p.get("water", 0)),
        keypad=registry.make_keypad(
            [[registry.B("shield_buy")], [registry.B("main_menu")]]
        ),
    )


registry.handle_shield = handle_shield


def handle_buy_shield(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    cost = 150
    if p.get("water", 0) < cost:
        registry.send(
            chat_id,
            registry.T("errors.not_enough_water", need=cost, have=p.get("water", 0)),
            keypad=registry.main_keypad(chat_id),
        )
        return
    p["water"] -= cost
    p["shield_until"] = registry.iso(
        registry.now() + timedelta(seconds=registry.SHIELD_DURATION)
    )
    registry.log_action(chat_id, "buy_shield", {"cost": cost})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("shield.bought", water=p["water"]),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_buy_shield = handle_buy_shield
