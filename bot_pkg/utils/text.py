from typing import Any


def build_meta_bold(text: str, phrases: list[tuple[str, int] | str]) -> list[dict]:
    """
    برای هر phrase، اگه توی text پیدا شد یک بولد اضافه می‌کند؛
    اگه پیدا نشد، بی‌سروصدا رد می‌شود.
    """
    meta: list[dict] = []

    for item in phrases:
        if isinstance(item, tuple):
            search, length = item
        else:
            search, length = item, len(item)

        idx = text.find(search)
        if idx == -1:
            continue

        meta.append(
            {
                "type": "Bold",
                "from_index": idx,
                "length": length,
            }
        )

    return meta or None


def bidi(value: Any) -> str:
    return f"\u2068{value}\u2069"


def fmt_num(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def display_name(value: Any) -> str:
    return bidi(str(value or "بی‌نام"))


def xp_bar(xp: int, max_xp: int, width: int = 10) -> str:
    filled = min(width, int(xp / max(1, max_xp) * width))
    pct = int(xp / max(1, max_xp) * 100)

    return "⬛" * filled + "⬜" * (width - filled) + f" {pct}%"
