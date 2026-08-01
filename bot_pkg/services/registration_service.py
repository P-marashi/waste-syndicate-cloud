"""Pure text parsing/normalization extracted from `s12_h_registration.py`.

Covers: referral-code extraction from a /start payload, and the name
normalization used to check for duplicate/reserved garage names.
`apply_referral`'s reward amounts are fixed constants (no formula, no
randomness) — not extracted, since there's no real computation to unit
test there.
"""

from __future__ import annotations

import re


def extract_ref_from_start(text: str) -> str | None:
    match = re.search(r"REF\d{4,}", text or "", re.IGNORECASE)
    return match.group(0).upper() if match else None


def normalize_unique_name(name: str) -> str:
    """Collapses whitespace and lowercases, so 'Ali  Baba' and 'ali baba'
    are treated as the same garage name for uniqueness checks.
    """
    return " ".join((name or "").strip().lower().split())


def is_reserved_name(value: str, reserved_names: set[str]) -> bool:
    """`reserved_names` should already include menu/button labels — kept
    injectable since that list is i18n/config data, not logic."""
    norm = normalize_unique_name(value)
    return norm in {normalize_unique_name(x) for x in reserved_names if x}
