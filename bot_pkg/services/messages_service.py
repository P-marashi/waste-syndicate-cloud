"""Pure private-message composition helpers extracted from
`s20_h_messages.py`. This module is mostly I/O/state-flow (chat_states,
send, save_game) with very little actual math — this is a small,
low-risk slice: text truncation and retention-log trimming, the two
places a subtle off-by-one would be easy to miss and hard to notice in
manual testing (you'd need >90 chars, or >MAX_PRIVATE_MESSAGES messages,
to even see it).
"""

from __future__ import annotations

import re


def message_preview(text: str, limit: int = 90) -> str:
    """Collapses whitespace and truncates for inbox list previews,
    appending an ellipsis when truncated.
    """
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def normalize_message_body(text: str, max_len: int = 700) -> str:
    """Strips whitespace and hard-caps message length."""
    return (text or "").strip()[:max_len]


def is_body_too_short(text: str, min_len: int = 2) -> bool:
    return len((text or "").strip()) < min_len


def trim_message_log(messages: list, max_count: int) -> list:
    """Keeps only the most recent `max_count` messages (oldest dropped
    first) — the retention policy for `private_messages`.
    """
    if max_count <= 0:
        return []
    return messages[-max_count:]
