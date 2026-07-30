import re
from typing import Any

from .registry import registry


def admin_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("admin_broadcast"), registry.B("admin_stats")],
            [registry.B("admin_messages"), registry.B("admin_players")],
            [registry.B("admin_rename_player"), registry.B("admin_rename_alliance")],
            [registry.B("admin_ban_player"), registry.B("admin_unban_player")],
            [registry.B("admin_penalty_player")],
            [registry.B("admin_alliances"), registry.B("admin_market")],
            [registry.B("main_menu")],
        ]
    )


registry.admin_keypad = admin_keypad


def admin_cancel_keypad() -> dict[str, Any]:
    return registry.make_keypad([[registry.B("admin_panel"), registry.B("main_menu")]])


registry.admin_cancel_keypad = admin_cancel_keypad


def handle_admin_panel(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.send(chat_id, registry.T("admin.panel"), keypad=registry.admin_keypad())


registry.handle_admin_panel = handle_admin_panel


def migrate_player_building_bonuses(chat_id: str) -> None:
    """یک بار برای همه بازیکن\u200cها بونوس ساختمان\u200cهای قدیمی رو اعمال کن"""
    p = registry.get_player(chat_id)
    registry.apply_building_bonuses(p)


registry.migrate_player_building_bonuses = migrate_player_building_bonuses


def handle_admin_stats(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    rows = registry.ranked_players()
    top_player = "—"
    top_score = 0
    if rows:
        top_player = registry.display_name(registry.player_name(rows[0][0]))
        top_score = rows[0][1]
    registry.send(
        chat_id,
        registry.T(
            "admin.stats",
            players=sum(
                1
                for p in registry.game.get("players", {}).values()
                if p.get("registered")
            ),
            alliances=len(registry.game.get("alliances", {})),
            orders=len(registry.open_orders()),
            season_id=registry.game.get("season", {}).get("id", 1),
            top_player=top_player,
            top_score=top_score,
            messages=len(registry.game.get("private_messages", [])),
            market_supply=sum(
                int(v) for v in registry.game.get("market_supply", {}).values()
            ),
            vault_total=sum(
                int(al.get("vault", 0))
                for al in registry.game.get("alliances", {}).values()
            ),
        ),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_stats = handle_admin_stats


def handle_admin_messages(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    rows = registry.game.get("private_messages", [])[-12:]
    if not rows:
        registry.send(
            chat_id, registry.T("admin.messages_empty"), keypad=registry.admin_keypad()
        )
        return
    lines = []
    for m in reversed(rows):
        lines.append(
            registry.T(
                "admin.message_line",
                id=m.get("id"),
                time=registry.fmt_dt(m.get("at")),
                sender=registry.player_name(m.get("from", "")),
                target=registry.player_name(m.get("to", "")),
                text=registry.message_preview(m.get("text", ""), 160),
            )
        )
    registry.send(
        chat_id,
        registry.T("admin.messages", lines="\n".join(lines)),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_messages = handle_admin_messages


def admin_players_page_button(page: int) -> str:
    return registry.T("admin.players_page_button", page=page)


registry.admin_players_page_button = admin_players_page_button


def admin_players_keypad(page: int, pages: int) -> dict[str, Any]:
    rows: list[list[str]] = []
    nav: list[str] = []
    if page > 1:
        nav.append(registry.admin_players_page_button(page - 1))
    if page < pages:
        nav.append(registry.admin_players_page_button(page + 1))
    if nav:
        rows.append(nav)
    rows.append([registry.B("admin_panel")])
    rows.append([registry.B("main_menu")])
    return registry.make_keypad(rows)


registry.admin_players_keypad = admin_players_keypad


def parse_admin_players_page(text: str) -> int | None:
    m = re.match("^👥 بازیکن\u200cها صفحه (\\d+)$", text.strip())
    if not m:
        return None
    try:
        return max(1, int(m.group(1)))
    except Exception:
        return None


registry.parse_admin_players_page = parse_admin_players_page


def handle_admin_players(chat_id: str, page: int = 1, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    ranked = registry.ranked_players(include_banned=True)
    total = len(ranked)
    pages = max(
        1,
        (total + registry.ADMIN_PLAYERS_PAGE_SIZE - 1)
        // registry.ADMIN_PLAYERS_PAGE_SIZE,
    )
    page = min(max(1, page), pages)
    start = (page - 1) * registry.ADMIN_PLAYERS_PAGE_SIZE
    rows = []
    for idx, (cid, score) in enumerate(
        ranked[start : start + registry.ADMIN_PLAYERS_PAGE_SIZE], start=start + 1
    ):
        p = registry.game.get("players", {}).get(cid, {})
        rows.append(
            registry.T(
                "admin.player_line",
                rank=idx,
                name=registry.player_name(cid),
                level=registry.fmt_num(p.get("level", 1)),
                water=registry.fmt_num(p.get("water", 0)),
                alliance=p.get("alliance") or "—",
                score=registry.fmt_num(score),
                status=registry.T("admin.player_status_banned")
                if p.get("banned")
                else registry.T("admin.player_status_active"),
            )
        )
    registry.send(
        chat_id,
        registry.T(
            "admin.players",
            page=page,
            pages=pages,
            total=registry.fmt_num(total),
            from_rank=registry.fmt_num(start + 1 if total else 0),
            to_rank=registry.fmt_num(
                min(start + registry.ADMIN_PLAYERS_PAGE_SIZE, total)
            ),
            lines="\n\n".join(rows) or "—",
        ),
        keypad=registry.admin_players_keypad(page, pages),
    )


registry.handle_admin_players = handle_admin_players


def handle_admin_alliances(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    lines = []
    for name, al in sorted(
        registry.game.get("alliances", {}).items(),
        key=lambda x: int(x[1].get("vault", 0)),
        reverse=True,
    )[:15]:
        lines.append(
            registry.T(
                "admin.alliance_line",
                name=name,
                owner=registry.player_name(al.get("owner")),
                count=len(al.get("members", [])),
                vault=al.get("vault", 0),
                level=registry.cartel_level(al),
                label=registry.cartel_level_data(al).get("label"),
            )
        )
    registry.send(
        chat_id,
        registry.T("admin.alliances", lines="\n".join(lines) or "—"),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_alliances = handle_admin_alliances


def handle_admin_market(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    supply_lines = []
    for r in registry.RESOURCES:
        supply_lines.append(
            registry.T(
                "admin.market_supply_line",
                icon=registry.RES_ICON[r],
                name=registry.RES_NAME[r],
                qty=int(registry.game.get("market_supply", {}).get(r, 0)),
                buy=registry.system_reference_price(r),
                sell=registry.system_buy_price(r),
            )
        )
    registry.send(
        chat_id,
        registry.T(
            "admin.market",
            orders=len(registry.open_orders()),
            supply="\n".join(supply_lines),
        ),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_market = handle_admin_market


def handle_admin_broadcast_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_admin_broadcast"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.broadcast_prompt"),
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_admin_broadcast_prompt = handle_admin_broadcast_prompt


def handle_admin_broadcast(chat_id: str, text: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    count = 0
    for cid, player in list(registry.game.get("players", {}).items()):
        if cid == chat_id or not player.get("registered") or player.get("banned"):
            continue
        registry.send(
            cid,
            registry.T("admin.broadcast_header", message=text),
            keypad=registry.main_keypad(cid),
        )
        count += 1
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.broadcast_done", count=count),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_broadcast = handle_admin_broadcast


def player_name_exists(name: str, exclude: str | None = None) -> bool:
    norm = (name or "").strip().lower()
    for cid, p in registry.game.get("players", {}).items():
        if exclude is not None and cid == exclude:
            continue
        if p.get("name", "").strip().lower() == norm:
            return True
    return False


registry.player_name_exists = player_name_exists


def find_alliance_by_name(name: str) -> str | None:
    norm = (name or "").strip().lower()
    if not norm:
        return None
    for aname in registry.game.get("alliances", {}).keys():
        if aname.strip().lower() == norm:
            return aname
    for aname in registry.game.get("alliances", {}).keys():
        if norm in aname.strip().lower():
            return aname
    return None


registry.find_alliance_by_name = find_alliance_by_name


def handle_admin_rename_player_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_player_target"
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.rename_player_target_prompt"),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_rename_player_prompt = handle_admin_rename_player_prompt


def handle_admin_rename_player_target(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    target = registry.find_player_by_name(text)
    if not target or not registry.game.get("players", {}).get(target, {}).get(
        "registered"
    ):
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_player_name",
        "target": target,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "admin.rename_player_name_prompt", player=registry.player_name(target)
        ),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_rename_player_target = handle_admin_rename_player_target


def handle_admin_rename_player_name(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    p = registry.game.get("players", {}).get(target or "")
    new_name = registry.clean_name(text, 24)
    if not target or not p:
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    if not new_name:
        registry.send(
            chat_id, registry.T("admin.bad_name"), keypad=registry.admin_cancel_keypad()
        )
        return
    if registry.player_name_exists(new_name, exclude=target):
        registry.send(
            chat_id,
            registry.T("admin.name_taken"),
            keypad=registry.admin_cancel_keypad(),
        )
        return
    old_name = p.get("name") or registry.player_name(target)
    p["name"] = new_name
    registry.log_action(
        target,
        "admin_rename_player",
        {"old": old_name, "new": new_name, "admin": chat_id},
    )
    registry.admin_audit(
        chat_id, "rename_player", {"target": target, "old": old_name, "new": new_name}
    )
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    registry.send(
        target,
        registry.T("admin.rename_player_notice", old=old_name, new=new_name),
        keypad=registry.main_keypad(target),
    )
    registry.send(
        chat_id,
        registry.T("admin.rename_player_done", old=old_name, new=new_name),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_rename_player_name = handle_admin_rename_player_name


def handle_admin_rename_alliance_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_alliance_target"
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.rename_alliance_target_prompt"),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_rename_alliance_prompt = handle_admin_rename_alliance_prompt


def handle_admin_rename_alliance_target(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    old_name = registry.find_alliance_by_name(text)
    if not old_name:
        registry.send(
            chat_id,
            registry.T("admin.alliance_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_alliance_name",
        "old_name": old_name,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.rename_alliance_name_prompt", alliance=old_name),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_rename_alliance_target = handle_admin_rename_alliance_target


def handle_admin_rename_alliance_name(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    old_name = st.get("old_name")
    new_name = registry.clean_name(text, 24)
    if not old_name or old_name not in registry.game.get("alliances", {}):
        registry.send(
            chat_id,
            registry.T("admin.alliance_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    if not new_name:
        registry.send(
            chat_id, registry.T("admin.bad_name"), keypad=registry.admin_cancel_keypad()
        )
        return
    if new_name in registry.game.get("alliances", {}) and new_name != old_name:
        registry.send(
            chat_id,
            registry.T("admin.alliance_name_taken"),
            keypad=registry.admin_cancel_keypad(),
        )
        return
    al = registry.game["alliances"].pop(old_name)
    al["name"] = new_name
    registry.alliance_log(
        al,
        "admin_rename_alliance",
        {"old": old_name, "new": new_name, "admin": chat_id},
    )
    registry.game["alliances"][new_name] = al
    for p in registry.game.get("players", {}).values():
        if p.get("alliance") == old_name:
            p["alliance"] = new_name
    registry.admin_audit(chat_id, "rename_alliance", {"old": old_name, "new": new_name})
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    for member in al.get("members", []):
        if member in registry.game.get("players", {}):
            registry.send(
                member,
                registry.T("admin.rename_alliance_notice", old=old_name, new=new_name),
                keypad=registry.main_keypad(member),
            )
    registry.send(
        chat_id,
        registry.T(
            "admin.rename_alliance_done",
            old=old_name,
            new=new_name,
            count=len(al.get("members", [])),
        ),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_rename_alliance_name = handle_admin_rename_alliance_name


def handle_admin_ban_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_admin_ban_target"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.ban_target_prompt"),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_ban_prompt = handle_admin_ban_prompt


def handle_admin_ban_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = registry.find_player_by_name(text)
    if not target or not registry.game.get("players", {}).get(target, {}).get(
        "registered"
    ):
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_ban_reason",
        "target": target,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.ban_reason_prompt", player=registry.player_name(target)),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_ban_target = handle_admin_ban_target


def handle_admin_ban_reason(chat_id: str, text: str, sender_id: str = "") -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    p = registry.game.get("players", {}).get(target or "")
    if not target or not p:
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    reason = registry.message_preview(text or "بدون دلیل ثبت\u200cشده", 180)
    p["banned"] = True
    p["ban_reason"] = reason
    p["banned_at"] = registry.iso(registry.now())
    p["banned_by"] = chat_id
    registry.log_action(target, "admin_ban", {"admin": chat_id, "reason": reason})
    registry.admin_audit(chat_id, "ban_player", {"target": target, "reason": reason})
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    registry.send(
        target,
        registry.T("admin.ban_notice_to_player", reason=reason),
        keypad=registry.make_keypad([[registry.B("help")]]),
    )
    registry.send(
        chat_id,
        registry.T(
            "admin.ban_done", player=registry.player_name(target), reason=reason
        ),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_ban_reason = handle_admin_ban_reason


def handle_admin_unban_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_admin_unban_target"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.unban_target_prompt"),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_unban_prompt = handle_admin_unban_prompt


def handle_admin_unban_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = registry.find_player_by_name(text)
    if not target or not registry.game.get("players", {}).get(target, {}).get(
        "registered"
    ):
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    p = registry.game["players"][target]
    p["banned"] = False
    p["ban_reason"] = ""
    p["banned_at"] = None
    p["banned_by"] = None
    registry.log_action(target, "admin_unban", {"admin": chat_id})
    registry.admin_audit(chat_id, "unban_player", {"target": target})
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    registry.send(
        target,
        registry.T("admin.unban_notice_to_player"),
        keypad=registry.main_keypad(target),
    )
    registry.send(
        chat_id,
        registry.T("admin.unban_done", player=registry.player_name(target)),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_unban_target = handle_admin_unban_target
registry.PENALTY_ALIASES = {
    "water": "water",
    "آب": "water",
    "scrap": "scrap",
    "اوراق": "scrap",
    "آهن": "scrap",
    "اهن": "scrap",
    "plastic": "plastic",
    "پلاستیک": "plastic",
    "glass": "glass",
    "شیشه": "glass",
    "شيشه": "glass",
    "battery": "battery",
    "باتری": "battery",
    "باطری": "battery",
    "copper": "copper",
    "مس": "copper",
    "xp": "xp",
    "تجربه": "xp",
    "score": "score",
    "points": "score",
    "امتیاز": "score",
    "رتبه": "score",
    "honor": "honor",
    "افتخار": "honor",
    "hp": "hp",
    "جان": "hp",
}


def parse_admin_penalty(text: str) -> tuple[dict[str, int], str]:
    raw = (text or "").strip()
    reason = "بدون دلیل ثبت\u200cشده"
    m = re.search("(?:^|\\s)(?:دلیل|reason)\\s*[=:]\\s*(.+)$", raw, re.IGNORECASE)
    if m:
        reason = registry.message_preview(m.group(1), 180)
        raw = raw[: m.start()].strip()
    items: dict[str, int] = {}
    for key, amount in re.findall("([A-Za-z_آ-یي]+)\\s*[=:]\\s*(-?\\d+)", raw):
        mapped = registry.PENALTY_ALIASES.get(
            key.strip()
        ) or registry.PENALTY_ALIASES.get(key.strip().lower())
        if not mapped:
            continue
        value = abs(int(amount))
        if value <= 0:
            continue
        items[mapped] = items.get(mapped, 0) + value
    return (items, reason)


registry.parse_admin_penalty = parse_admin_penalty


def apply_admin_penalty(target: str, penalties: dict[str, int]) -> list[str]:
    p = registry.game["players"][target]
    lines: list[str] = []
    for key, amount in penalties.items():
        if key == "water":
            before = int(p.get("water", 0))
            taken = min(before, amount)
            p["water"] = before - taken
            lines.append(
                registry.T(
                    "admin.penalty_change_line",
                    label="💧 آب",
                    amount=registry.fmt_num(taken),
                    now=registry.fmt_num(p["water"]),
                )
            )
        elif key in registry.RESOURCES:
            before = int(p.get("resources", {}).get(key, 0))
            taken = min(before, amount)
            p.setdefault("resources", {})[key] = before - taken
            lines.append(
                registry.T(
                    "admin.penalty_change_line",
                    label=f"{registry.RES_ICON[key]} {registry.RES_NAME[key]}",
                    amount=registry.fmt_num(taken),
                    now=registry.fmt_num(p["resources"][key]),
                )
            )
        elif key == "xp":
            before = int(p.get("xp", 0))
            taken = min(before, amount)
            p["xp"] = before - taken
            lines.append(
                registry.T(
                    "admin.penalty_change_line",
                    label="⭐ تجربه",
                    amount=registry.fmt_num(taken),
                    now=registry.fmt_num(p["xp"]),
                )
            )
        elif key == "score":
            p["season_points_bonus"] = int(p.get("season_points_bonus", 0)) - amount
            lines.append(
                registry.T(
                    "admin.penalty_score_line",
                    amount=registry.fmt_num(amount),
                    now=registry.fmt_num(registry.season_score(target)),
                )
            )
        elif key == "honor":
            p["honor"] = int(p.get("honor", 0)) - amount
            lines.append(
                registry.T(
                    "admin.penalty_change_line",
                    label="🎖️ افتخار",
                    amount=registry.fmt_num(amount),
                    now=registry.fmt_num(p["honor"]),
                )
            )
        elif key == "hp":
            before = int(p.get("hp", 100))
            taken = min(before, amount)
            p["hp"] = max(0, before - taken)
            lines.append(
                registry.T(
                    "admin.penalty_change_line",
                    label="❤️ جان",
                    amount=registry.fmt_num(taken),
                    now=registry.fmt_num(p["hp"]),
                )
            )
    return lines


registry.apply_admin_penalty = apply_admin_penalty


def handle_admin_penalty_prompt(chat_id: str, sender_id: str = "") -> None:
    if not registry.is_admin(chat_id, sender_id):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_admin_penalty_target"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.penalty_target_prompt"),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_penalty_prompt = handle_admin_penalty_prompt


def handle_admin_penalty_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = registry.find_player_by_name(text)
    if not target or not registry.game.get("players", {}).get(target, {}).get(
        "registered"
    ):
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_admin_penalty_details",
        "target": target,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("admin.penalty_details_prompt", player=registry.player_name(target)),
        keypad=registry.admin_cancel_keypad(),
    )


registry.handle_admin_penalty_target = handle_admin_penalty_target


def handle_admin_penalty_details(chat_id: str, text: str, sender_id: str = "") -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    if not target or target not in registry.game.get("players", {}):
        registry.send(
            chat_id,
            registry.T("admin.player_not_found"),
            keypad=registry.admin_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        registry.save_game()
        return
    penalties, reason = registry.parse_admin_penalty(text)
    if not penalties:
        registry.send(
            chat_id,
            registry.T("admin.penalty_bad_format"),
            keypad=registry.admin_cancel_keypad(),
        )
        return
    before_score = registry.season_score(target)
    lines = registry.apply_admin_penalty(target, penalties)
    after_score = registry.season_score(target)
    p = registry.game["players"][target]
    note = {
        "admin": chat_id,
        "penalties": penalties,
        "reason": reason,
        "before_score": before_score,
        "after_score": after_score,
    }
    p.setdefault("admin_notes", []).append({"at": registry.iso(registry.now()), **note})
    p["admin_notes"] = p["admin_notes"][-30:]
    registry.log_action(target, "admin_penalty", note)
    registry.admin_audit(chat_id, "penalty_player", {"target": target, **note})
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    registry.send(
        target,
        registry.T(
            "admin.penalty_notice_to_player", reason=reason, lines="\n".join(lines)
        ),
        keypad=registry.main_keypad(target),
    )
    registry.send(
        chat_id,
        registry.T(
            "admin.penalty_done",
            player=registry.player_name(target),
            before=registry.fmt_num(before_score),
            after=registry.fmt_num(after_score),
            reason=reason,
            lines="\n".join(lines),
        ),
        keypad=registry.admin_keypad(),
    )


registry.handle_admin_penalty_details = handle_admin_penalty_details


def handle_help(chat_id: str) -> None:
    ev = registry.current_event()
    event_text = (
        registry.T("world.current", title=ev["title"], effect_text=ev["effect_text"])
        if ev
        else registry.T("world.none")
    )
    registry.send(
        chat_id,
        registry.T("help.text") + "\n\n" + event_text,
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_help = handle_help
