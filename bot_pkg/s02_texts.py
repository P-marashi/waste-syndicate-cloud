import json
import os
import random
from typing import Any

from .registry import registry

registry.TEXTS: dict[str, Any] = {}

# این فایل‌های تکه‌ای مستقیم روی ریشه‌ی TEXTS merge میشن،
# به جای اینکه زیر اسم فایلشون nest بشن
# (مثلاً texts/meta.json می‌ره مستقیم رو ریشه، نه TEXTS["meta"])
registry.MERGE_TO_ROOT = {"raid_extra", "meta"}


def load_offset():
    if not os.path.exists(registry.OFFSET_FILE):
        return None
    try:
        with open(registry.OFFSET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("next_offset_id")
    except Exception:
        return None


registry.load_offset = load_offset


def save_offset(offset):
    if not offset:
        return
    try:
        with open(registry.OFFSET_FILE, "w", encoding="utf-8") as f:
            json.dump({"next_offset_id": offset}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[OFFSET]", e)


registry.save_offset = save_offset


def skip_old_updates():
    """
    موقع روشن شدن بات،
    تمام پیام\u200cهای قدیمی فقط خوانده میشن
    ولی Process نمیشن.
    """
    print("⏩ Skipping pending updates...")
    offset = registry.load_offset()
    while True:
        payload = {"limit": 100}
        if offset:
            payload["offset_id"] = offset
        resp = registry.api("getUpdates", payload)
        updates = resp.get("updates", [])
        next_offset = resp.get("next_offset_id")
        if next_offset:
            offset = next_offset
            registry.save_offset(offset)
        if not updates:
            break
    print("✅ Bot synced.")


registry.skip_old_updates = skip_old_updates


def deep_get(d: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


registry.deep_get = deep_get


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


registry.deep_merge = deep_merge


def load_texts() -> None:
    registry.TEXTS = {}

    # ── اولویت با پوشه‌ی texts/ (فایل‌های split‌شده) ──────────
    texts_dir = getattr(registry, "TEXTS_DIR", None)
    if texts_dir is not None and texts_dir.is_dir():
        files = sorted(texts_dir.glob("*.json"))
        if files:
            for path in files:
                with path.open("r", encoding="utf-8") as f:
                    chunk = json.load(f)

                stem = path.stem
                if not isinstance(chunk, dict):
                    registry.TEXTS[stem] = chunk
                    continue

                if stem in registry.MERGE_TO_ROOT:
                    registry.TEXTS = registry.deep_merge(registry.TEXTS, chunk)
                else:
                    # buttons.json → TEXTS["buttons"] = ...
                    registry.TEXTS[stem] = chunk

            print(f"✅ Texts loaded from folder: {texts_dir} ({len(files)} files)")
            return

    # # ── حالت قدیمی: یک فایل تکی ──────────────────────────────
    # if not registry.TEXTS_FILE.exists():
    #     raise SystemExit(
    #         f"Text folder/file not found.\n"
    #         f"  folder: {texts_dir}\n"
    #         f"  file:   {registry.TEXTS_FILE}"
    #     )
    # with registry.TEXTS_FILE.open("r", encoding="utf-8") as f:
    #     registry.TEXTS = json.load(f)
    # print(f"✅ Texts loaded from single file: {registry.TEXTS_FILE}")


registry.load_texts = load_texts


def T(key: str, **kwargs: Any) -> str:
    val = registry.deep_get(registry.TEXTS, key, key)
    if isinstance(val, list):
        val = random.choice(val)
    if not isinstance(val, str):
        return str(val)
    try:
        return val.format(**kwargs)
    except Exception:
        return val


registry.T = T


def B(key: str) -> str:
    return registry.T(f"buttons.{key}")


registry.B = B
