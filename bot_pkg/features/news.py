from ..registry import registry


def handle_news(chat_id: str) -> None:
    feed = registry.game.get("news_feed", [])[:12]
    if not feed:
        registry.send(
            chat_id, registry.T("news.empty"), keypad=registry.main_keypad(chat_id)
        )
        return
    lines = []
    for item in feed:
        lines.append(
            registry.T(
                "news.line",
                time=registry.fmt_dt(item.get("at")),
                text=item.get("text", ""),
            )
        )
    registry.send(
        chat_id,
        registry.T("news.text", lines="\n".join(lines)),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_news = handle_news
