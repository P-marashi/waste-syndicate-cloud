from typing import Any

from .registry import registry

registry._ux_prev_main_keypad = registry.main_keypad
registry._ux_prev_dispatch = registry.dispatch
registry._ux_prev_handle_state = registry.handle_state


def ux_global_nav_buttons() -> set[str]:
    """دکمه\u200cهایی که باید از هر state متنی بیرون بزنند و همان صفحه را باز کنند."""
    keys = [
        "main_menu",
        "profile",
        "city_map",
        "scavenge",
        "market",
        "attack",
        "inventory",
        "craft",
        "buildings",
        "alliance",
        "leaderboard",
        "daily_missions",
        "daily",
        "open_cache",
        "season",
        "messages",
        "event",
        "help",
        "back_market",
        "world_boss",
        "news",
        "night_smuggler",
        "revenge_menu",
        "bounty_board",
        "territories",
        "alliance_missions",
        "admin_panel",
    ]
    vals = {
        registry.B(k)
        for k in keys
        if registry.B(k) and (not registry.B(k).startswith("buttons."))
    }
    vals.update(
        {"/start", "start", "شروع", "منو", "منوی اصلی", "لغو", "cancel", "Cancel"}
    )
    return vals


registry.ux_global_nav_buttons = ux_global_nav_buttons


def clear_chat_state(chat_id: str) -> bool:
    """اگر کاربر در ورودی متنی گیر کرده باشد، state پاک می\u200cشود."""
    states = registry.game.setdefault("chat_states", {})
    if chat_id in states:
        states.pop(chat_id, None)
        registry.save_game()
        return True
    return False


registry.clear_chat_state = clear_chat_state


def main_keypad(chat_id: str | None = None, sender_id: str = "") -> dict[str, Any]:
    """منوی اصلی مرتب\u200cشده بر اساس کارهای پرتکرار و هاب\u200cهای مهم."""
    rows = [
        [registry.B("profile"), registry.B("city_map")],
        [registry.B("market"), registry.B("attack")],
        [registry.B("craft"), registry.B("buildings")],
        [registry.B("alliance"), registry.B("inventory")],
        [registry.B("season"), registry.B("leaderboard")],
        [registry.B("invite")],
        [registry.B("help")],
    ]
    if chat_id and registry.is_admin(chat_id, sender_id):
        rows.append([registry.B("admin_panel")])
    return registry.make_keypad(rows)


registry.main_keypad = main_keypad
