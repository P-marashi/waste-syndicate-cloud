import re
from typing import Any


def safe_int(s: Any, default: int = 0) -> int:
    try:
        return int(str(s).strip())
    except Exception:
        return default


def clean_name(
    value: str,
    max_len: int = 24,
) -> str | None:
    value = re.sub(r"\s+", " ", (value or "").strip())
    value = value.replace("\n", " ")

    if len(value) < 2 or len(value) > max_len:
        return None

    if any(
        x in value.lower()
        for x in [
            "http",
            "@",
            "/",
            "\\",
            "<",
            ">",
            "{",
        ]
    ):
        return None

    return value
