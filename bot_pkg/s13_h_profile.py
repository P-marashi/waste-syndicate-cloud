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
