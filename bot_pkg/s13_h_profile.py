from typing import Any

from .registry import registry


def profile_upgrades_text(p: dict[str, Any]) -> str:
    ups = p.get("upgrades_in_progress", [])
    if not ups:
        return registry.T("profile.upgrades_none")
    lines = [registry.T("profile.upgrades_title")]
    for u in ups:
        bk = u.get("bldg")
        if bk not in registry.BUILDINGS:
            continue
        lines.append(
            registry.T(
                "profile.upgrade_line",
                label=registry.BUILDINGS[bk]["label"],
                level=u.get("to_level", "؟"),
                time=registry.fmt_cd(
                    (
                        registry.fromiso(u.get("finish"), registry.now())
                        - registry.now()
                    ).total_seconds()
                ),
            )
        )
    return "\n".join(lines) if len(lines) > 1 else registry.T("profile.upgrades_none")


registry.profile_upgrades_text = profile_upgrades_text


def handle_start(chat_id: str, name: str = "") -> None:
    p = registry.get_player(chat_id, name)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    registry.recalc_power(p)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "start.welcome", name=p.get("name") or registry.player_name(chat_id)
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_start = handle_start


def handle_profile(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    finished = registry.finish_upgrades(p)
    for u in finished:
        registry.send(
            chat_id,
            registry.T(
                "buildings.finished",
                label=registry.BUILDINGS[u["bldg"]]["label"],
                level=u["to_level"],
            ),
        )
    registry.recalc_power(p)
    lv, xp, mx, label = registry.level_info(p)
    stats = p.get("stats", {})
    sh = registry.shield_remaining(p)
    shield_line = (
        registry.T("profile.shield_active", time=registry.fmt_cd(sh))
        if sh
        else registry.T("profile.shield_off")
    )
    total_sv = stats.get("scavenges", 0)
    ok_sv = stats.get("scavenge_success", 0)
    fail_sv = max(0, total_sv - ok_sv)
    rate = f"{int(ok_sv / max(1, total_sv) * 100)}%" if total_sv else "0%"
    al = p.get("alliance") or "ندارم"
    txt = registry.T(
        "profile.text",
        name=registry.display_name(p.get("name")),
        season_id=registry.game.get("season", {}).get("id", 1),
        season_left=registry.season_left_text(),
        level_label=label,
        scavenge_ready="✅" if registry.cd_remaining(p, "scavenge") == 0 else "💤",
        scavenge_cd=registry.fmt_cd(registry.cd_remaining(p, "scavenge")),
        raid_ready="✅" if registry.cd_remaining(p, "raid") == 0 else "💤",
        raid_cd=registry.fmt_cd(registry.cd_remaining(p, "raid")),
        shield_line=shield_line,
        honor=p.get("honor", 0),
        honor_title=registry.honor_title(p.get("honor", 0)),
        level=lv,
        xp=xp,
        max_xp=mx,
        xp_bar=registry.xp_bar(xp, mx),
        hp=p.get("hp", 100),
        water=p.get("water", 0),
        scrap=p["resources"].get("scrap", 0),
        plastic=p["resources"].get("plastic", 0),
        glass=p["resources"].get("glass", 0),
        battery=p["resources"].get("battery", 0),
        copper=p["resources"].get("copper", 0),
        attack=f"{p.get('total_attack', 0):,}",
        defense=f"{p.get('total_defense', 0):,}",
        power=f"{p.get('total_attack', 0) + p.get('total_defense', 0):,}",
        alliance=al,
        alliance_shared=stats.get("alliance_shared", 0),
        scavenges=total_sv,
        scavenge_success=ok_sv,
        scavenge_fail=fail_sv,
        scavenge_rate=rate,
        raids_done=stats.get("raids_done", 0),
        raids_received=stats.get("raids_received", 0),
        base_status=registry.base_status_label(p),
        upgrades=registry.profile_upgrades_text(p),
    )
    txt += "\n\n" + registry.profile_daily_missions_text(chat_id)
    meta = registry.build_meta_bold(
        txt, [(txt[:25], 25), "سطح:", "حمله:", "دفاع:", "افتخار:"]
    )
    registry.save_game()
    registry.send(chat_id, txt, keypad=registry.main_keypad(chat_id), meta_data=meta)


registry.handle_profile = handle_profile
