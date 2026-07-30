from ..registry import registry


def handle_event(chat_id: str) -> None:
    """
    نمایش رویداد فعال روز برای کاربر.
    """

    event = registry.current_event()

    if not event:
        registry.send(
            chat_id,
            "🌪️ رویداد روز\n\nفعلاً هیچ رویدادی فعال نیست.",
            keypad=registry.main_keypad(chat_id),
        )
        return

    remaining = registry.fmt_cd(
        (
            registry.fromiso(
                event.get("expires_at"),
                registry.now(),
            )
            - registry.now()
        ).total_seconds()
    )

    registry.send(
        chat_id,
        (
            "🌪️ رویداد روز\n\n"
            f"{event['title']}\n"
            f"{event['desc']}\n\n"
            f"📌 اثر:\n{event['effect_text']}\n\n"
            f"⏳ زمان باقی‌مانده: {remaining}"
        ),
        keypad=registry.main_keypad(chat_id),
    )
