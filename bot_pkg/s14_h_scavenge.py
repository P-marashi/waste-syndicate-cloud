from typing import Any

from .registry import registry
from .services import scavenge_service


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
        risk, chance = scavenge_service.compute_chance(
            z, risk_modifier=int(registry.event_mod("risk", 0))
        )
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

    # --- pure game logic: dice roll, loot table, risk math ------------
    # (bot_pkg/services/scavenge_service.py — unit-tested independently)
    outcome = scavenge_service.roll_scavenge(
        zone_key,
        z,
        risk_modifier=int(registry.event_mod("risk", 0)),
        loot_multiplier=registry.event_mod("loot", 1.0),
        rare_loot_multiplier=registry.event_mod("rare_loot", 1.0),
    )

    registry.inc_mission(chat_id, "scavenge", 1)
    registry.set_cd(p, "scavenge", outcome.cooldown_seconds)

    # --- everything below is still handler territory: player mutation -
    # that depends on other not-yet-extracted registry helpers (XP/level,
    # caches, legendary drops), plus all message formatting and I/O.
    if outcome.success:
        scavenge_service.apply_success(p, outcome)
        level_up = registry.add_xp(p, z["xp"])
        registry.save_game()

        loot_str = registry.fmt_res_lines(outcome.loot)
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
            chat_id, "scavenge_success", {"zone": zone_key, "loot": outcome.loot}
        )
        msg = registry.T(
            "scavenge.success",
            zone=registry.B(z["label_key"]),
            story=registry.T("scavenge.stories_success"),
            loot=loot_str,
            xp=int(z["xp"] * registry.event_mod("xp", 1.0)),
            chance=outcome.chance,
            roll=outcome.roll,
            level_msg=lvl_msg,
            alliance_note=registry.T("scavenge.no_share"),
            cooldown=registry.fmt_cd(outcome.cooldown_seconds),
        )
    else:
        lost = scavenge_service.apply_failure(p, outcome)
        registry.save_game()

        lost_str = registry.fmt_res_loss(lost)
        registry.log_action(
            chat_id,
            "scavenge_fail",
            {"zone": zone_key, "damage": outcome.damage, "lost": lost},
        )
        msg = registry.T(
            "scavenge.fail",
            zone=registry.B(z["label_key"]),
            story=registry.T("scavenge.stories_fail"),
            damage=outcome.damage,
            hp=p["hp"],
            lost=lost_str,
            chance=outcome.chance,
            roll=outcome.roll,
            cooldown=registry.fmt_cd(outcome.cooldown_seconds),
        )

    registry.save_game()
    registry.send(chat_id, msg, keypad=registry.main_keypad(chat_id))


registry.handle_scavenge = handle_scavenge
