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
        [registry.B("alliance_group_raid"), registry.B("alliance_vault")],
        [registry.B("alliance_leave")],
    ]
    if al.get("owner") == chat_id:
        rows.insert(0, [registry.B("alliance_manage")])
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
                [registry.B("alliance_kick"), registry.B("alliance_vault")],
                [registry.B("alliance_upgrade"), registry.B("alliance_group_raid")],
                [registry.B("alliance"), registry.B("main_menu")],
            ]
        ),
    )


registry.handle_alliance_manage = handle_alliance_manage


def handle_toggle_alliance(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    al["open"] = not bool(al.get("open"))
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.mode_changed", mode=registry.alliance_mode_text(al)),
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_toggle_alliance = handle_toggle_alliance


def handle_alliance_upgrade(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    lv = registry.cartel_level(al)
    if lv >= registry.MAX_CARTEL_LEVEL:
        registry.send(
            chat_id,
            registry.T("alliance.upgrade_max"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    cost = registry.cartel_next_upgrade_cost(al)
    vault = int(al.get("vault", 0))
    if vault < cost:
        registry.send(
            chat_id,
            registry.T("alliance.upgrade_not_enough", need=cost, have=vault),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    al["vault"] = vault - cost
    al["level"] = lv + 1
    registry.alliance_log(
        al, "cartel_upgrade", {"from_level": lv, "to_level": lv + 1, "cost": cost}
    )
    registry.save_game()
    msg = registry.T(
        "alliance.upgraded",
        level=al["level"],
        label=registry.cartel_level_data(al).get("label"),
        cost=cost,
        perks=registry.cartel_perks_text(al),
    )
    for cid in al.get("members", []):
        if cid in registry.game["players"]:
            registry.send(cid, msg, keypad=registry.main_keypad(cid))


registry.handle_alliance_upgrade = handle_alliance_upgrade


def handle_applicants(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    apps = [cid for cid in al.get("applicants", []) if cid in registry.game["players"]]
    if not apps:
        registry.send(
            chat_id,
            registry.T("alliance.applicants_empty"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    lines = [f"- {registry.player_name(cid)}" for cid in apps]
    rows = []
    for cid in apps[:6]:
        rows.append(
            [f"قبول: {registry.player_name(cid)}", f"رد: {registry.player_name(cid)}"]
        )
    rows.append([registry.B("alliance_manage"), registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T("alliance.applicants", lines="\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_applicants = handle_applicants


def handle_applicant_decision(chat_id: str, text: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    accept = text.startswith("قبول:")
    name = text.split(":", 1)[1].strip()
    target = registry.find_player_by_name(name, al.get("applicants", []))
    if not target:
        registry.send(
            chat_id,
            registry.T("alliance.kick_not_found"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    al["applicants"].remove(target)
    if accept:
        if len(al.get("members", [])) >= registry.ALLIANCE_MAX:
            registry.send(
                chat_id,
                registry.T("alliance.full"),
                keypad=registry.alliance_keypad(chat_id),
            )
            return
        al["members"].append(target)
        registry.game["players"][target]["alliance"] = al["name"]
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("alliance.approved", player=registry.player_name(target)),
            keypad=registry.alliance_keypad(chat_id),
        )
        registry.send(
            target,
            registry.T("alliance.joined", name=al["name"]),
            keypad=registry.main_keypad(target),
        )
    else:
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("alliance.rejected", player=registry.player_name(target)),
            keypad=registry.alliance_keypad(chat_id),
        )


registry.handle_applicant_decision = handle_applicant_decision


def handle_kick_prompt(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    members = [cid for cid in al.get("members", []) if cid != chat_id]
    registry.game["chat_states"][chat_id] = {"state": "awaiting_kick_member"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "alliance.kick_prompt",
            members="\n".join(f"- {registry.player_name(cid)}" for cid in members)
            or "عضوی نداری",
        ),
        keypad=registry.make_keypad(
            [[registry.B("alliance_manage"), registry.B("main_menu")]]
        ),
    )


registry.handle_kick_prompt = handle_kick_prompt


def handle_kick_member(chat_id: str, text: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    members = [cid for cid in al.get("members", []) if cid != chat_id]
    target = registry.find_player_by_name(text, members)
    if not target:
        registry.send(
            chat_id,
            registry.T("alliance.kick_not_found"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    al["members"].remove(target)
    registry.game["players"][target]["alliance"] = None
    registry.game["chat_states"].pop(chat_id, None)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.kicked", player=registry.player_name(target)),
        keypad=registry.alliance_keypad(chat_id),
    )
    registry.send(
        target,
        registry.T("alliance.kicked_notice", alliance=al["name"]),
        keypad=registry.main_keypad(target),
    )


registry.handle_kick_member = handle_kick_member
