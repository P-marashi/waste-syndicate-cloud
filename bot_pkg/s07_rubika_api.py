import json
import time
from typing import Any

import requests

from .registry import registry


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


def make_keypad(rows: list[list[str]]) -> dict[str, Any]:
    return {
        "rows": [
            {
                "buttons": [
                    {"id": txt, "type": "Simple", "button_text": txt} for txt in row
                ]
            }
            for row in rows
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


registry.make_keypad = make_keypad


def main_keypad(chat_id: str | None = None, sender_id: str = "") -> dict[str, Any]:
    rows = [
        [registry.B("profile"), registry.B("city_map")],
        [registry.B("market"), registry.B("buildings")],
        [registry.B("craft"), registry.B("attack")],
        [registry.B("alliance"), registry.B("inventory")],
        [registry.B("daily_missions"), registry.B("daily")],
        [registry.B("season"), registry.B("leaderboard")],
        [registry.B("messages"), registry.B("event")],
        [registry.B("help")],
    ]
    if chat_id and registry.is_admin(chat_id, sender_id):
        rows.append([registry.B("admin_panel")])
    return registry.make_keypad(rows)


registry.main_keypad = main_keypad


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
