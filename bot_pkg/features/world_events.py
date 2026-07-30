import random
from datetime import timedelta
from typing import Any

from ..registry import registry


def current_event() -> dict[str, Any] | None:
    ev = registry.game.get("world_event_active")
    if not ev:
        return None
    if registry.fromiso(ev.get("expires_at"), registry.now()) <= registry.now():
        registry.game["world_event_active"] = None
        return None
    return ev


registry.current_event = current_event


def event_mod(key: str, default: float = 1.0) -> float:
    ev = registry.current_event()
    if not ev:
        return default
    mods = ev.get("mods", {})
    return float(mods.get(key, default))


registry.event_mod = event_mod


def maybe_daily_event() -> None:
    today = registry.today_key()
    if registry.game.get("last_daily_event") == today:
        return
    if registry.now().hour < registry.DAILY_EVENT_HOUR:
        return
    ev = dict(random.choice(registry.DAILY_EVENTS))
    ev["started_at"] = registry.iso(registry.now())
    ev["expires_at"] = registry.iso(registry.now() + timedelta(hours=24))
    registry.game["world_event_active"] = ev
    registry.game["last_daily_event"] = today
    registry.apply_event_one_time(ev)
    registry.send_group_radio(
        registry.T(
            "group_radio.daily_event",
            title=ev["title"],
            desc=ev["desc"],
            effect_text=ev["effect_text"],
        ),
        force=True,
        reason="daily_event",
    )
    for cid in list(registry.game["players"].keys()):
        if registry.game["players"][cid].get("registered"):
            registry.send(
                cid,
                registry.T(
                    "world.daily_event",
                    title=ev["title"],
                    desc=ev["desc"],
                    effect_text=ev["effect_text"],
                ),
                keypad=registry.main_keypad(cid),
            )
    registry.save_game()


registry.maybe_daily_event = maybe_daily_event


def apply_event_one_time(ev: dict[str, Any]) -> None:
    kind = ev.get("one_time")
    if not kind:
        return
    for p in registry.game["players"].values():
        if not p.get("registered"):
            continue
        if kind == "acid":
            wall = int(p.get("buildings", {}).get("wall", 0))
            if wall < 2:
                p["hp"] = max(1, int(p.get("hp", 100)) - random.randint(6, 16))
        elif kind == "heal":
            p["hp"] = min(100, int(p.get("hp", 100)) + random.randint(10, 25))
        elif kind == "airdrop":
            for r in ["scrap", "plastic", "glass"]:
                p.setdefault("resources", {})[r] = p.get("resources", {}).get(
                    r, 0
                ) + random.randint(4, 14)


registry.apply_event_one_time = apply_event_one_time
