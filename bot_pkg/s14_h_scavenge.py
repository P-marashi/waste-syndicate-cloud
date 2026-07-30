import random
from typing import Any

from .registry import registry


def scavenge_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("scavenge_alley"), registry.B("scavenge_suburb")],
            [registry.B("scavenge_center"), registry.B("scavenge_bunker")],
            [registry.B("main_menu")],
        ]
    )


registry.scavenge_keypad = scavenge_keypad


def handle_scavenge_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    if registry.cd_remaining(p, "scavenge") > 0:
        registry.send(
            chat_id,
            registry.T(
                "scavenge.cooldown",
                time=registry.fmt_cd(registry.cd_remaining(p, "scavenge")),
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    lines = []
    for key, z in registry.ZONES.items():
        risk = max(0, z["risk"] + int(registry.event_mod("risk", 0)))
        chance = max(5, min(95, 100 - risk * 12))
        lines.append(
            registry.T(
                "scavenge.zone_line",
                label=registry.B(z["label_key"]),
                desc=z["desc"],
                chance=chance,
                loot_min=z["loot_min"],
                loot_max=z["loot_max"],
                xp=z["xp"],
            )
        )
    ev = registry.current_event()
    event_line = ""
    if ev:
        event_line = f"\n\n🌪️ رویداد فعال: {ev['title']}\n📌 {ev['effect_text']}"
    registry.send(
        chat_id,
        registry.T("scavenge.menu", zones="\n".join(lines) + event_line),
        keypad=registry.scavenge_keypad(),
    )


registry.handle_scavenge_menu = handle_scavenge_menu


def zone_by_label(text: str) -> str | None:
    for key, z in registry.ZONES.items():
        if text == registry.B(z["label_key"]):
            return key
    return None


registry.zone_by_label = zone_by_label


def handle_scavenge(chat_id: str, zone_key: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    if registry.cd_remaining(p, "scavenge") > 0:
        registry.send(
            chat_id,
            registry.T(
                "scavenge.cooldown",
                time=registry.fmt_cd(registry.cd_remaining(p, "scavenge")),
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    z = registry.ZONES[zone_key]
    risk = max(0, z["risk"] + int(registry.event_mod("risk", 0)))
    chance = max(5, min(95, 100 - risk * 12))
    roll = random.randint(1, 100)
    p["stats"]["scavenges"] = p["stats"].get("scavenges", 0) + 1
    registry.inc_mission(chat_id, "scavenge", 1)
    base_cd = z["cd_min"] * 60
    loot_note = ""
    if roll <= chance:
        p["stats"]["scavenge_success"] = p["stats"].get("scavenge_success", 0) + 1
        total = random.randint(z["loot_min"], z["loot_max"])
        total = int(total * registry.event_mod("loot", 1.0))
        pool = ["scrap", "plastic", "glass", "battery", "copper"]
        weights = {
            "alley": [42, 35, 18, 3, 2],
            "suburb": [30, 28, 24, 10, 8],
            "center": [22, 20, 24, 18, 16],
            "bunker": [15, 15, 20, 25, 25],
        }[zone_key]
        rare_mod = registry.event_mod("rare_loot", 1.0)
        weights[3] = int(weights[3] * rare_mod)
        weights[4] = int(weights[4] * rare_mod)
        loot: dict[str, int] = {}
        for _ in range(total):
            r = random.choices(pool, weights=weights)[0]
            loot[r] = loot.get(r, 0) + 1
            p["resources"][r] = p["resources"].get(r, 0) + 1
        level_up = registry.add_xp(p, z["xp"])
        registry.set_cd(p, "scavenge", base_cd)
        registry.save_game()
        loot_str = registry.fmt_res_lines(loot)
        extra_lines = []
        cache_note = registry.maybe_find_cache(chat_id, zone_key)
        if cache_note:
            extra_lines.append(cache_note)
        legendary_note = registry.maybe_award_legendary(
            chat_id, "گشت\u200cزنی", chance=0.001
        )
        if legendary_note:
            extra_lines.append(legendary_note)
        if extra_lines:
            loot_str += "\n\n" + "\n".join(extra_lines)
        lvl_msg = registry.T("scavenge.level_up", level=p["level"]) if level_up else ""
        registry.log_action(
            chat_id, "scavenge_success", {"zone": zone_key, "loot": loot}
        )
        msg = registry.T(
            "scavenge.success",
            zone=registry.B(z["label_key"]),
            story=registry.T("scavenge.stories_success"),
            loot=loot_str,
            xp=int(z["xp"] * registry.event_mod("xp", 1.0)),
            chance=chance,
            roll=roll,
            level_msg=lvl_msg,
            alliance_note=loot_note or registry.T("scavenge.no_share"),
            cooldown=registry.fmt_cd(base_cd),
        )
    else:
        damage = random.randint(5, 20 + risk * 3)
        p["hp"] = max(1, p.get("hp", 100) - damage)
        lost = {}
        for r in registry.RESOURCES:
            have = p["resources"].get(r, 0)
            if have > 0:
                qty = random.randint(0, min(3, have))
                if qty:
                    p["resources"][r] -= qty
                    lost[r] = qty
        lost_str = registry.fmt_res_loss(lost)
        registry.set_cd(p, "scavenge", base_cd)
        registry.save_game()
        registry.log_action(
            chat_id, "scavenge_fail", {"zone": zone_key, "damage": damage, "lost": lost}
        )
        msg = registry.T(
            "scavenge.fail",
            zone=registry.B(z["label_key"]),
            story=registry.T("scavenge.stories_fail"),
            damage=damage,
            hp=p["hp"],
            lost=lost_str,
            chance=chance,
            roll=roll,
            cooldown=registry.fmt_cd(base_cd),
        )
    registry.save_game()
    registry.send(chat_id, msg, keypad=registry.main_keypad(chat_id))


registry.handle_scavenge = handle_scavenge
