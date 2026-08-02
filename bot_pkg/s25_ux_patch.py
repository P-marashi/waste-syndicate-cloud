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
        "alliance_members",
        "alliance_treasury",
        "alliance_requests",
        "settings",
        "history",
        "inbox",
        "game_news",
        "search_player",
        "achievements",
        "stats",
        "resources",
        "equipment",
        "special_items",
        "buy",
        "sell",
        "barter",
        "my_orders",
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
    if registry.chat_state_repo.exists(chat_id):
        registry.chat_state_repo.delete(chat_id)
        return True
    return False


registry.clear_chat_state = clear_chat_state
