import random
import re
from typing import Any

from .registry import registry


def private_message_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [[registry.B("messages_send")], [registry.B("main_menu")]]
    )


registry.private_message_keypad = private_message_keypad


def private_message_story() -> str:
    stories = registry.T("messages.stories")
    if isinstance(stories, str):
        return stories
    return random.choice(
        stories or ["یک پیک ناشناس از دل خرابه\u200cها پیام را رساند."]
    )


registry.private_message_story = private_message_story


def message_preview(text: str, limit: int = 90) -> str:
    text = re.sub("\\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "…"


registry.message_preview = message_preview


def handle_messages_menu(chat_id: str) -> None:
    inbox = [
        m for m in registry.game.get("private_messages", []) if m.get("to") == chat_id
    ][-5:]
    if not inbox:
        body = registry.T("messages.inbox_empty")
    else:
        lines = []
        for m in reversed(inbox):
            lines.append(
                registry.T(
                    "messages.inbox_line",
                    id=m.get("id"),
                    sender=registry.player_name(m.get("from", "")),
                    time=registry.fmt_dt(m.get("at")),
                    preview=registry.message_preview(m.get("text", "")),
                )
            )
        body = registry.T("messages.inbox", lines="\n".join(lines))
    registry.send(chat_id, body, keypad=registry.private_message_keypad())


registry.handle_messages_menu = handle_messages_menu


def handle_private_message_target_prompt(chat_id: str) -> None:
    registry.game["chat_states"][chat_id] = {"state": "awaiting_private_message_target"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("messages.target_prompt"),
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_private_message_target_prompt = handle_private_message_target_prompt


def handle_private_message_target(chat_id: str, text: str) -> None:
    target = registry.find_player_by_name(text)
    if not target or not registry.game["players"].get(target, {}).get("registered"):
        registry.send(
            chat_id,
            registry.T("messages.target_not_found"),
            keypad=registry.private_message_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    if target == chat_id:
        registry.send(
            chat_id,
            registry.T("messages.cannot_self"),
            keypad=registry.private_message_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_private_message_body",
        "target": target,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("messages.body_prompt", target=registry.player_name(target)),
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_private_message_target = handle_private_message_target


def handle_private_message_body(chat_id: str, text: str) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    if not target or target not in registry.game.get("players", {}):
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("messages.target_not_found"),
            keypad=registry.private_message_keypad(),
        )
        return
    body = (text or "").strip()
    if len(body) < 2:
        registry.send(
            chat_id,
            registry.T("messages.body_too_short"),
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    body = body[:700]
    mid = int(registry.game.get("next_private_message_id", 1))
    registry.game["next_private_message_id"] = mid + 1
    story = registry.private_message_story()
    record = {
        "id": mid,
        "from": chat_id,
        "to": target,
        "text": body,
        "story": story,
        "at": registry.iso(registry.now()),
    }
    registry.game.setdefault("private_messages", []).append(record)
    registry.game["private_messages"] = registry.game["private_messages"][
        -registry.MAX_PRIVATE_MESSAGES :
    ]
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.log_action(
        chat_id, "private_message_sent", {"to": target, "message_id": mid}
    )
    registry.log_action(
        target, "private_message_received", {"from": chat_id, "message_id": mid}
    )
    registry.save_game()
    registry.send(
        target,
        registry.T(
            "messages.delivered_to_target",
            sender=registry.player_name(chat_id),
            story=story,
            message=body,
        ),
        keypad=registry.main_keypad(target),
    )
    registry.send(
        chat_id,
        registry.T("messages.sent", target=registry.player_name(target), id=mid),
        keypad=registry.private_message_keypad(),
    )


registry.handle_private_message_body = handle_private_message_body
