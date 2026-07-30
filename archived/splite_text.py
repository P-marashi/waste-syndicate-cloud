#!/usr/bin/env python3
"""
split_texts.py — شکستن waste_syndicate_texts_fa.json به فایل‌های کوچک

اجرا:
  python split_texts.py
  python split_texts.py --src waste_syndicate_texts_fa.json --out texts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# اگر بخوای چند کلید را داخل یک فایل نگه داری:
GROUPED: dict[str, list[str]] = {
    "raid_extra": [
        "button",
        "bucket_line",
        "direct_line",
        "drone_hint",
        "drone_available",
        "need_drone",
        "no_bucket_targets",
        "mode_random",
        "mode_direct",
        "low_hp",
    ],
}


def split_texts(src: Path, out_dir: Path) -> None:
    if not src.exists():
        raise SystemExit(f"❌ فایل پیدا نشد: {src}")

    with src.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise SystemExit("❌ ریشه JSON باید یک object باشد.")

    out_dir.mkdir(parents=True, exist_ok=True)

    # کلیدهایی که داخل GROUPED هستند را جدا جمع می‌کنیم
    grouped_keys: set[str] = set()
    for keys in GROUPED.values():
        grouped_keys.update(keys)

    written: list[str] = []

    # ۱) فایل‌های گروهی (اختیاری)
    for group_name, keys in GROUPED.items():
        chunk = {}
        for k in keys:
            if k in data:
                chunk[k] = data[k]
        if not chunk:
            continue
        path = out_dir / f"{group_name}.json"
        path.write_text(
            json.dumps(chunk, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path.name)
        print(f"  ✓ {path.name}  ({', '.join(chunk.keys())})")

    # ۲) بقیه کلیدها — هر کدام یک فایل
    for key, value in data.items():
        if key in grouped_keys:
            continue
        path = out_dir / f"{key}.json"
        # محتوای فایل = فقط همان بخش (بدون کلید بیرونی اضافه)
        # load_texts قبلی: TEXTS[stem] = chunk
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path.name)
        kind = type(value).__name__
        print(f"  ✓ {path.name}  ({kind})")

    print(f"\n✅ تمام — {len(written)} فایل در {out_dir.resolve()}")
    print("   حالا load_texts را طوری بگذار که پوشه texts/ را بخواند.")


def main() -> None:
    p = argparse.ArgumentParser(description="Split bot texts JSON into smaller files")
    p.add_argument(
        "--src",
        type=Path,
        default=Path("waste_syndicate_texts_fa.json"),
        help="مسیر JSON اصلی",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("texts"),
        help="پوشه خروجی",
    )
    args = p.parse_args()
    print(f"📂 Source: {args.src}")
    print(f"📁 Output: {args.out}\n")
    split_texts(args.src, args.out)


if __name__ == "__main__":
    main()
