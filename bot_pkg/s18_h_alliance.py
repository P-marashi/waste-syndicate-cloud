from typing import Any

from .registry import registry


def alliance_keypad(chat_id: str) -> dict[str, Any]:
    p = registry.get_player(chat_id)
    al = registry.player_alliance(chat_id)
    if not al:
        return registry.make_keypad(
            [
                [registry.B("alliance_create"), registry.B("alliance_list")],
                [registry.B("main_menu")],
            ]
        )
    rows = [
        [registry.B("alliance_members"), registry.B("alliance_treasury")],
        [registry.B("alliance_requests"), registry.B("alliance_group_raid")],
    ]
    if al.get("owner") == chat_id:
        rows.append([registry.B("alliance_manage")])
    rows.append([registry.B("main_menu")])
    return registry.make_keypad(rows)


registry.alliance_keypad = alliance_keypad


def handle_alliance_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    lines = []
    for cid in al.get("members", []):
        mp = registry.game["players"].get(cid)
        if mp:
            registry.recalc_power(mp)
            lines.append(
                registry.T(
                    "alliance.member_line",
                    name=mp.get("name"),
                    level=mp.get("level", 1),
                    water=mp.get("water", 0),
                    power=f"{mp.get('total_attack', 0) + mp.get('total_defense', 0):,}",
                )
            )
    registry.send(
        chat_id,
        registry.T(
            "alliance.view",
            name=al.get("name"),
            owner=registry.player_name(al.get("owner")),
            mode=registry.alliance_mode_text(al),
            count=len(al.get("members", [])),
            max_members=registry.ALLIANCE_MAX,
            members="\n".join(lines),
            vault=al.get("vault", 0),
            shared=al.get("total_shared", 0),
            cartel_level=registry.cartel_level(al),
            cartel_label=registry.cartel_level_data(al).get("label"),
            perks=registry.cartel_perks_text(al),
            next_cost=registry.cartel_next_upgrade_cost(al)
            or registry.T("alliance.max_level"),
        ),
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_alliance_menu = handle_alliance_menu


def handle_create_alliance_prompt(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    if p.get("alliance"):
        registry.send(
            chat_id,
            registry.T("alliance.already_member"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_alliance_name"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.create_prompt"),
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_create_alliance_prompt = handle_create_alliance_prompt


def handle_create_alliance(chat_id: str, text: str) -> None:
    p = registry.get_player(chat_id)
    name = registry.clean_name(text, 24)
    if not name:
        registry.send(
            chat_id,
            registry.T("alliance.bad_name"),
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    if name in registry.game["alliances"]:
        registry.send(
            chat_id,
            registry.T("alliance.exists"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if p.get("alliance"):
        registry.send(
            chat_id,
            registry.T("alliance.already_member"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    registry.game["alliances"][name] = {
        "name": name,
        "owner": chat_id,
        "members": [chat_id],
        "open": True,
        "applicants": [],
        "vault": 0,
        "total_shared": 0,
        "level": 1,
        "created_at": registry.iso(registry.now()),
        "log": [],
    }
    p["alliance"] = name
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(chat_id, "alliance_create", {"name": name})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.created", name=name),
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_create_alliance = handle_create_alliance


def handle_list_alliances(chat_id: str) -> None:
    if not registry.game["alliances"]:
        registry.send(
            chat_id,
            registry.T("alliance.list_empty"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    lines, rows = ([], [])
    for name, al in list(registry.game["alliances"].items())[:12]:
        lines.append(
            registry.T(
                "alliance.list_line",
                status=registry.alliance_mode_text(al),
                name=name,
                count=len(al.get("members", [])),
                max_members=registry.ALLIANCE_MAX,
                owner=registry.player_name(al.get("owner")),
            )
        )
        rows.append([registry.T("alliance.join_button", name=name)])
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T("alliance.list", lines="\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_list_alliances = handle_list_alliances


def handle_join_alliance(chat_id: str, text: str) -> None:
    p = registry.get_player(chat_id)
    if p.get("alliance"):
        registry.send(
            chat_id,
            registry.T("alliance.already_member"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    name = text.split(":", 1)[1].strip() if ":" in text else text.strip()
    al = registry.game["alliances"].get(name)
    if not al:
        registry.send(
            chat_id,
            registry.T("market.order_not_found"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if len(al.get("members", [])) >= registry.ALLIANCE_MAX:
        registry.send(
            chat_id,
            registry.T("alliance.full"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if al.get("open"):
        al["members"].append(chat_id)
        p["alliance"] = name
        registry.log_action(chat_id, "alliance_join", {"name": name})
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("alliance.joined", name=name),
            keypad=registry.alliance_keypad(chat_id),
        )
    else:
        if chat_id not in al.setdefault("applicants", []):
            al["applicants"].append(chat_id)
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("alliance.requested", name=name),
            keypad=registry.alliance_keypad(chat_id),
        )
        if al.get("owner") in registry.game["players"]:
            registry.send(
                al["owner"],
                registry.T(
                    "alliance.request_notice", alliance=name, player=p.get("name")
                ),
                keypad=registry.alliance_keypad(al["owner"]),
            )


registry.handle_join_alliance = handle_join_alliance


def handle_leave_alliance(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    al = registry.player_alliance(chat_id)
    if not al:
        registry.handle_alliance_menu(chat_id)
        return
    if al.get("owner") == chat_id and len(al.get("members", [])) > 1:
        registry.send(
            chat_id,
            registry.T("alliance.owner_cant_leave"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    name = al.get("name")
    if chat_id in al.get("members", []):
        al["members"].remove(chat_id)
    p["alliance"] = None
    if not al.get("members"):
        registry.game["alliances"].pop(name, None)
    registry.log_action(chat_id, "alliance_leave", {"name": name})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.left", name=name),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_leave_alliance = handle_leave_alliance


def handle_alliance_manage(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    registry.send(
        chat_id,
        registry.T(
            "alliance.manage",
            name=al.get("name"),
            mode=registry.alliance_mode_text(al),
            applicants=len(al.get("applicants", [])),
            count=len(al.get("members", [])),
            max_members=registry.ALLIANCE_MAX,
            vault=al.get("vault", 0),
            cartel_level=registry.cartel_level(al),
            cartel_label=registry.cartel_level_data(al).get("label"),
            next_cost=registry.cartel_next_upgrade_cost(al)
            or registry.T("alliance.max_level"),
        ),
        keypad=registry.make_keypad(
            [
                [registry.B("alliance_open_toggle"), registry.B("alliance_applicants")],
                [registry.B("alliance_kick"), registry.B("alliance_upgrade")],
                [registry.B("alliance")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_alliance_manage = handle_alliance_manage


# ── New: Alliance Members ──


def handle_alliance_members(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    members = []
    for cid in al.get("members", []):
        mp = registry.game["players"].get(cid)
        if mp:
            registry.recalc_power(mp)
            owner_tag = " 👑" if cid == al.get("owner") else ""
            members.append(
                f"• {mp.get('name', 'بی‌نام')}{owner_tag}"
                f" — سطح {mp.get('level', 1)}"
                f" | قدرت {mp.get('total_attack', 0) + mp.get('total_defense', 0):,}"
            )
    text = registry.T(
        "alliance.members_list",
        name=al.get("name"),
        count=len(members),
        max_members=registry.ALLIANCE_MAX,
        members="\n".join(members) or "هیچ عضوی نیست!",
    )
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad(
            [
                [registry.B("alliance")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_alliance_members = handle_alliance_members


# ── New: Alliance Treasury ──


def handle_alliance_treasury(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    p = registry.get_player(chat_id)
    vault = int(al.get("vault", 0))
    shared = int(al.get("total_shared", 0))
    my_shared = int(p.get("stats", {}).get("alliance_shared", 0))
    lv = registry.cartel_level(al)
    cartel_data = registry.cartel_level_data(al)
    next_cost = registry.cartel_next_upgrade_cost(al)
    text = registry.T(
        "alliance.treasury_view",
        name=al.get("name"),
        vault=f"{vault:,}",
        total_shared=f"{shared:,}",
        my_shared=f"{my_shared:,}",
        cartel_level=lv,
        cartel_label=cartel_data.get("label") if cartel_data else "-",
        next_upgrade_cost=(
            f"{next_cost:,}" if next_cost else registry.T("alliance.max_level")
        ),
    )
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad(
            [
                [registry.B("alliance_upgrade"), registry.B("alliance_vault")],
                [registry.B("alliance")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_alliance_treasury = handle_alliance_treasury


# ── New: Alliance Requests ──


def handle_alliance_requests(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    apps = [cid for cid in al.get("applicants", []) if cid in registry.game["players"]]
    if not apps:
        registry.send(
            chat_id,
            registry.T("alliance.no_requests"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    lines = []
    rows = []
    for cid in apps[:6]:
        mp = registry.game["players"][cid]
        lines.append(f"• {mp.get('name', 'بی‌نام')} — سطح {mp.get('level', 1)}")
        rows.append([f"قبول: {mp.get('name')}", f"رد: {mp.get('name')}"])
    text = registry.T(
        "alliance.requests_list",
        name=al.get("name"),
        count=len(apps),
        list="\n".join(lines),
    )
    rows.append([registry.B("alliance")])
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad(rows),
    )


registry.handle_alliance_requests = handle_alliance_requests
