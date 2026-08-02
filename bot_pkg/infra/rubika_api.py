"""Raw Rubika Bot API client — HTTP only, no game logic, no keypad/text
formatting. `make_keypad`/`main_keypad` used to live in this file too;
they're presentation concerns and now live in
`bot_pkg/presentation/keypads.py` instead.
"""

import json
import time
from typing import Any

import requests

from ..registry import registry


def api(
    method: str, payload: dict[str, Any] | None = None, retries: int = 3
) -> dict[str, Any]:
    payload = payload or {}
    for attempt in range(retries):
        try:
            r = requests.post(f"{registry.API_BASE}/{method}", json=payload, timeout=12)
            if not r.text.strip() or r.text.strip().startswith("<!DOCTYPE"):
                raise ValueError("Invalid response (HTML or empty)")
            data = r.json()
            if registry.DEBUG or r.status_code != 200:
                print(f"[API {method}] HTTP={r.status_code} {data}")
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                return data["data"]
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, ValueError, requests.RequestException) as e:
            print(f"[API] {method} attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


registry.api = api


def send(
    chat_id: str,
    text: str,
    keypad: dict[str, Any] | None = None,
    remove_keypad: bool = False,
    meta_data: list[dict] | None = None,
) -> dict[str, Any]:
    payload = {"chat_id": chat_id, "text": text or " "}
    if meta_data:
        payload["meta_data"] = meta_data
    if not str(chat_id).startswith(("g", "c")):
        if keypad:
            payload["chat_keypad"] = keypad
            payload["chat_keypad_type"] = "New"
        elif remove_keypad:
            payload["chat_keypad_type"] = "Remove"
    return registry.api("sendMessage", payload)


registry.send = send
