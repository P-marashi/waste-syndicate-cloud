"""Keypad/button construction — presentation concerns, kept separate
from `infra/rubika_api.py`'s raw HTTP client. Extracted out of what
used to be `s07_rubika_api.py`, where a generic keypad builder and the
Rubika API client lived in the same file for no structural reason.
"""

from typing import Any

from ..registry import registry


def make_keypad(rows: list[list[str]]) -> dict[str, Any]:
    return {
        "rows": [
            {
                "buttons": [
                    {"id": txt, "type": "Simple", "button_text": txt} for txt in row
                ]
            }
            for row in rows
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


registry.make_keypad = make_keypad


def main_keypad(chat_id: str | None = None, sender_id: str = "") -> dict[str, Any]:
    rows = [
        [registry.B("city_map"), registry.B("garage")],
        [registry.B("attack"), registry.B("alliance")],
        [registry.B("buildings"), registry.B("craft")],
        [registry.B("market"), registry.B("inventory")],
        [registry.B("daily_missions"), registry.B("events")],
        [registry.B("season"), registry.B("leaderboard")],
        [registry.B("messages"), registry.B("more")],
        [registry.B("main_menu")],
    ]

    if chat_id and registry.is_admin(chat_id, sender_id):
        rows.append([registry.B("admin_panel")])

    return registry.make_keypad(rows)


registry.main_keypad = main_keypad
