from bot_pkg.registry import registry


def effective_sender_id(
    chat_id: str,
    sender_id: str = "",
) -> str:
    """
    در چت خصوصی روبیکا ممکن است chat_id با sender_id یکی نباشد.
    """

    return str(
        sender_id or registry.LAST_SENDER_BY_CHAT.get(str(chat_id), "") or chat_id
    )


def is_admin(
    chat_id: str,
    sender_id: str = "",
) -> bool:
    uid = effective_sender_id(
        chat_id,
        sender_id,
    )

    return uid in registry.ADMIN_IDS or str(chat_id) in registry.ADMIN_IDS


def is_group_admin(
    sender_id: str,
) -> bool:
    return str(sender_id) in registry.ADMIN_IDS


def is_banned(chat_id: str) -> bool:
    return bool(registry.game.get("players", {}).get(chat_id, {}).get("banned"))


def ban_reason(chat_id: str) -> str:
    return str(
        registry.game.get("players", {}).get(chat_id, {}).get("ban_reason")
        or "بدون دلیل ثبت‌شده"
    )
