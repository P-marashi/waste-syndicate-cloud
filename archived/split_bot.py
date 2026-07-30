#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_bot.py
════════════
Splits the monolithic Waste Syndicate bot file into many small, readable
files — ONE PER SECTION — using the section banners that are ALREADY in
your code:

    # ══════════════════════════════════════════════════════
    #  SECTION NAME
    # ══════════════════════════════════════════════════════

WHY THIS APPROACH (instead of manually rewriting the file into "real"
importable modules with `from x import y`):

Your script relies heavily on *definition order* — e.g. the "EXPANSION
PATCH" and "UX PATCH" sections literally redefine `new_player`,
`dispatch`, `handle_state`, `market_keypad`, etc. AFTER the originals,
and they capture the old versions as `_orig_xxx` before overriding them.
That only works if all the code still runs top-to-bottom inside ONE
shared namespace, exactly like it does today as a single file.

If we split it into normal Python modules that `import` each other,
every function's `__globals__` would be bound to the module it was
DEFINED in — not to some shared app-wide namespace — and all the
override/monkey-patch tricks (and a lot of the cross-file function
calls) would silently break or raise NameError. That is a real risk of
"looks fine, breaks in prod."

So instead this tool:
  1. Cuts the file into files at each banner boundary (never inside a
     function/dict/string — banners in this file only ever sit between
     top-level statements).
  2. Numbers the files in original order (01_, 02_, 03_, ...) so you can
     see the whole program's structure just by looking at the folder.
  3. Generates a tiny `run_bot.py` loader that `exec()`s each file, in
     order, into ONE shared dict — which is *exactly* what already
     happens when Python runs your single file today. Behavior is
     100% unchanged. Tracebacks still point at the correct split file
     and line number (because `compile()` is given the real filename),
     so debugging is actually easier than before, not harder.

USAGE
─────
    python split_bot.py path/to/waste_syndicate_bot_v4_seasonal.py -o out_dir

Then run the bot with:
    cd out_dir
    python run_bot.py

(Same env vars as before: BOT_TOKEN, ADMIN_IDS, GAME_GROUP_ID, etc.)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNER_LINE = re.compile(r"^#\s*═{10,}\s*$")
TITLE_LINE = re.compile(r"^#\s*(.+?)\s*$")

# Friendly, stable file-name slugs for the section titles we know this
# project uses. Anything not listed here is auto-slugified instead, so
# new sections you add later still get split correctly.
KNOWN_SLUGS = {
    "CONFIG": "config",
    "TEXT SYSTEM": "texts",
    "GAME TABLES": "gamedata",
    "GLOBAL GAME STATE": "state",
    "UTILITIES": "utils",
    "SAVE / LOAD / MIGRATION": "persistence",
    "RUBIKA API": "rubika_api",
    "PLAYER HELPERS": "player",
    "ALLIANCE ECONOMY": "alliance_economy",
    "WOW FEATURES: NEWS / MISSIONS / CACHES / BOSS / MAP / GROUP RAID": "world_features",
    "MARKET": "market_core",
    "HANDLERS: REGISTRATION": "h_registration",
    "HANDLERS: MAIN / PROFILE": "h_profile",
    "HANDLERS: SCAVENGE": "h_scavenge",
    "HANDLERS: MARKET": "h_market",
    "HANDLERS: BUILDINGS / CRAFT": "h_buildings_craft",
    "HANDLERS: RAID / SHIELD": "h_raid_shield",
    "HANDLERS: ALLIANCE": "h_alliance",
    "HANDLERS: INVENTORY / DAILY / INVITE / SEASON / LEADERBOARD / HELP": "h_misc",
    "HANDLERS: PLAYER MESSAGES": "h_messages",
    "HANDLERS: ADMIN": "h_admin",
    "STATE HANDLER / DISPATCHER": "dispatcher",
    "UPDATE PROCESSING": "update_processing",
    "EXPANSION PATCH: SEASON / SMUGGLER / REVENGE / BOUNTY / CACHES / TERRITORIES": "expansion_patch",
    "UX PATCH: SAFE STATE ESCAPE + CLEAN MAIN MENU": "ux_patch",
    "MAIN LOOP": "main_loop",
}


def slugify(title: str, index: int) -> str:
    key = re.sub(r"\s+", " ", title.strip())
    if key in KNOWN_SLUGS:
        base = KNOWN_SLUGS[key]
    else:
        base = re.sub(r"[^a-zA-Z0-9]+", "_", key.lower()).strip("_") or f"section{index}"
        base = base[:40]
    return f"{index:02d}_{base}.py"


def find_sections(lines: list[str]) -> list[tuple[str, int]]:
    """Return list of (title, line_index) for every banner-title-banner triple."""
    sections = []
    i = 0
    n = len(lines)
    while i < n - 2:
        if (
            BANNER_LINE.match(lines[i])
            and lines[i + 1].lstrip().startswith("#")
            and BANNER_LINE.match(lines[i + 2])
        ):
            title = lines[i + 1].lstrip("#").strip()
            sections.append((title, i))
            i += 3
        else:
            i += 1
    return sections


def split_file(src_path: Path, out_dir: Path) -> list[str]:
    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    sections = find_sections(lines)

    if not sections:
        raise SystemExit(
            "No section banners found. This script expects the "
            "'# ══...' / '#  TITLE' / '# ══...' banner style used in "
            "waste_syndicate_bot_v4_seasonal.py."
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    # Everything before the first banner (shebang, module docstring, imports)
    # becomes file 00_header.py.
    header_end = sections[0][1]
    chunks: list[tuple[str, str]] = []  # (filename, content)
    if header_end > 0:
        chunks.append(("00_header.py", "".join(lines[:header_end])))

    for idx, (title, start) in enumerate(sections, start=1):
        end = sections[idx][1] if idx < len(sections) else len(lines)
        content = "".join(lines[start:end])
        fname = slugify(title, idx)
        chunks.append((fname, content))

    written = []
    for fname, content in chunks:
        path = out_dir / fname
        path.write_text(content, encoding="utf-8")
        written.append(fname)
        # Safety check: make sure the cut didn't land mid-statement
        # (e.g. inside a multi-line dict/string). If a banner ever ends
        # up inside a data structure, this fails loudly right here
        # instead of producing a mysteriously broken bot later.
        try:
            compile(content, fname, "exec")
        except SyntaxError as e:
            raise SystemExit(
                f"\nSPLIT FAILED: {fname} is not valid standalone Python "
                f"({e}).\nThis means a section banner landed inside a "
                f"multi-line statement. Please report the section title "
                f"around this point so the banner list can be adjusted."
            )
        print(f"  wrote {fname:45s} ({content.count(chr(10))} lines)")

    return written


LOADER_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_bot.py — auto-generated loader.

This runs every split file, IN ORIGINAL ORDER, inside one shared global
namespace — exactly like Python already does for a single-file script.
This is what keeps the "EXPANSION PATCH" / "UX PATCH" override sections
working correctly (they redefine functions like `dispatch`, `new_player`,
`market_keypad`, etc. on top of the earlier definitions, on purpose).

Because each chunk is compiled with its own real filename, tracebacks
still point at the correct split file + line number, so this is not a
black box for debugging — it is the opposite: you can now open just the
80-line file that crashed instead of scrolling a 5,500-line one.

Regenerate this whole folder any time by re-running split_bot.py on the
current source file.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

FILES = {file_list}

def run() -> None:
    shared_globals: dict = {"__name__": "__main__", "__file__": str(HERE / "run_bot.py")}
    for fname in FILES:
        path = HERE / fname
        code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
        exec(code, shared_globals)
    # `main()` is defined in the last chunk (the MAIN LOOP section).
    shared_globals["main"]()

if __name__ == "__main__":
    run()
'''


def write_loader(out_dir: Path, written: list[str]) -> None:
    file_list_repr = "[\n" + "".join(f"    {f!r},\n" for f in written) + "]"
    loader = LOADER_TEMPLATE.replace("{file_list}", file_list_repr)
    (out_dir / "run_bot.py").write_text(loader, encoding="utf-8")
    print(f"  wrote run_bot.py (loader)")


def write_readme(out_dir: Path, written: list[str]) -> None:
    lines = [
        "# Split layout\n\n",
        "Generated by `split_bot.py`. Run the bot with:\n\n",
        "```\npython run_bot.py\n```\n\n",
        "Files, in the exact order they execute (same order as the original single file):\n\n",
    ]
    for f in written:
        lines.append(f"- `{f}`\n")
    lines.append(
        "\nEach file corresponds 1:1 to one of the `# ══...` section banners "
        "in the original script. Nothing was reordered or rewritten — the "
        "content of every file is an exact copy of that section, so behavior "
        "is unchanged. `run_bot.py` executes them in order into one shared "
        "namespace (equivalent to Python running the original single file), "
        "which is required because later sections (EXPANSION PATCH, UX PATCH) "
        "intentionally redefine functions from earlier sections.\n"
    )
    (out_dir / "SPLIT_README.md").write_text("".join(lines), encoding="utf-8")
    print("  wrote SPLIT_README.md")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="Path to the original bot .py file")
    ap.add_argument("-o", "--out", type=Path, default=Path("bot_split"), help="Output directory")
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"Source file not found: {args.source}")

    print(f"Splitting {args.source} -> {args.out}/")
    written = split_file(args.source, args.out)
    write_loader(args.out, written)
    write_readme(args.out, written)
    print(f"\nDone. {len(written)} files written.")
    print(f"Copy your waste_syndicate_texts_fa.json (and .env / save file) next to {args.out}/run_bot.py, then:")
    print(f"  cd {args.out} && python run_bot.py")


if __name__ == "__main__":
    main()
