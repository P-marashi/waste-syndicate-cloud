from typing import Any

from .registry import registry


def process_update(raw: dict[str, Any]) -> None:
    upd = raw.get("update", raw)
    if "inline_message" in raw:
        il = raw["inline_message"]
        chat_id = il.get("chat_id", "")
        aux = il.get("aux_data") or {}
        inline_sender_id = str(il.get("sender_id", chat_id))
        registry.LAST_SENDER_BY_CHAT[str(chat_id)] = inline_sender_id
        registry.dispatch(
            chat_id,
            il.get("text", ""),
            inline_sender_id[-6:],
            aux.get("button_id", ""),
            inline_sender_id,
        )
        return
    chat_id = upd.get("chat_id", "")
    msg = upd.get("new_message") or upd.get("updated_message") or {}
    if not msg or not chat_id:
        return
    text = msg.get("text", "") or ""
    aux = msg.get("aux_data") or {}
    bid = aux.get("button_id", "") or ""
    sender_id = str(msg.get("sender_id", chat_id))
    registry.LAST_SENDER_BY_CHAT[str(chat_id)] = sender_id
    sender_name = sender_id[-6:]
    if registry.DEBUG:
        print(f"[UPDATE] chat={chat_id} sender={sender_id} text={text!r} bid={bid!r}")
    if str(chat_id).startswith(("g", "c")):
        if str(chat_id) == str(registry.GAME_GROUP_ID):
            if registry.DEBUG:
                print(f"[GROUP RADIO] chat={chat_id} sender={sender_id} text={text!r}")
            registry.handle_group_message(
                str(chat_id), text or bid or "", str(sender_id)
            )
        elif registry.DEBUG:
            print(f"[GROUP IGNORED] chat={chat_id} sender={sender_id} text={text!r}")
        return
    registry.dispatch(chat_id, text or bid, sender_name, bid, sender_id)


registry.process_update = process_update
