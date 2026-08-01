"""Pure admin-panel math extracted from `s21_h_admin.py`.

Covers: player-list pagination (a classic off-by-one bug zone) and
penalty parsing/application (clamping so a penalty can't push a
resource negative, except honor/score which are allowed to go negative
by design).
"""

from __future__ import annotations

import re
from typing import Callable


def _truncate_with_ellipsis(text: str, limit: int) -> str:
    """Same truncation rule as messages_service.message_preview (collapse
    whitespace, ellipsis if over the limit) — duplicated here rather than
    imported so this module doesn't depend on which PR merges first.
    """
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def paginate(total_items: int, page: int, page_size: int) -> tuple[int, int, int, int]:
    """Returns (clamped_page, total_pages, start_index, end_index_exclusive).
    `page` gets clamped into [1, total_pages] rather than erroring on an
    out-of-range request — matches the original handler's behavior of
    silently correcting a bad page number instead of rejecting it.
    """
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = min(max(1, page), total_pages)
    start = (page - 1) * page_size
    end = min(start + page_size, total_items)
    return page, total_pages, start, end


def parse_page_number(text: str, pattern: str) -> int | None:
    """`pattern` must have exactly one capturing group for the page
    number (kept injectable since the exact button text is i18n data,
    e.g. "👥 بازیکن‌ها صفحه 3").
    """
    match = re.match(pattern, (text or "").strip())
    if not match:
        return None
    try:
        return max(1, int(match.group(1)))
    except (ValueError, IndexError):
        return None


def parse_penalty_text(
    text: str,
    resolve_key: Callable[[str], str | None],
    *,
    default_reason: str = "بدون دلیل ثبت‌شده",
    reason_max_len: int = 180,
) -> tuple[dict[str, int], str]:
    """Parses admin penalty commands like "water=50 xp=10 دلیل: تقلب".
    `resolve_key` maps a raw token to a canonical penalty key (kept
    injectable — the alias table is config data, not logic). Unknown
    keys and non-positive amounts are silently dropped, matching the
    original's lenient parsing (an admin typo shouldn't crash the flow).
    """
    raw = (text or "").strip()
    reason = default_reason

    reason_match = re.search(r"(?:^|\s)(?:دلیل|reason)\s*[=:]\s*(.+)$", raw, re.IGNORECASE)
    if reason_match:
        reason = _truncate_with_ellipsis(reason_match.group(1), reason_max_len)
        raw = raw[: reason_match.start()].strip()

    items: dict[str, int] = {}
    for key, amount in re.findall(r"([A-Za-z_آ-یي]+)\s*[=:]\s*(-?\d+)", raw):
        mapped = resolve_key(key.strip()) or resolve_key(key.strip().lower())
        if not mapped:
            continue
        value = abs(int(amount))
        if value <= 0:
            continue
        items[mapped] = items.get(mapped, 0) + value

    return items, reason


def apply_clamped_penalty(before: int, amount: int) -> tuple[int, int]:
    """For values that can't go negative (water, resources, xp, hp):
    takes at most `amount`, never more than `before` has. Returns
    (amount_actually_taken, value_after).
    """
    before = int(before)
    amount = max(0, int(amount))
    taken = min(before, amount)
    return taken, before - taken


def apply_unclamped_penalty(before: int, amount: int) -> int:
    """For values allowed to go negative (honor, season score bonus)."""
    return int(before) - int(amount)
