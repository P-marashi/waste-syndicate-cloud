import random
from datetime import timedelta
from typing import Any

from ..registry import registry
from ..services import group_raid_service


def alliance_group_raid_target(al: dict[str, Any]) -> dict[str, Any]:
    member_set = set(al.get("members", []))
    candidates = []
    for cid, p in registry.game.get("players", {}).items():
        if cid in member_set or not p.get("registered") or p.get("banned"):
            continue
        if registry.is_shielded(p):
            continue
        registry.recalc_power(p)
        power = group_raid_service.candidate_target_power(
            p.get("total_defense", 0), p.get("total_attack", 0), p.get("level", 1)
        )
        candidates.append((cid, p, power))
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        top = candidates[: min(5, len(candidates))]
        cid, p, power = random.choice(top)
        return {
            "type": "player",
            "chat_id": cid,
            "name": p.get("name"),
            "defense": group_raid_service.roll_player_target_defense(power),
            "water": int(p.get("water", 0)),
        }
    level = registry.cartel_level(al)
    return {
        "type": "npc",
        "chat_id": "",
        "name": random.choice(
            [
                "🏰 قلعه آهن‌خوارها",
                "☢️ برج نگهبانان بنکر",
                "🦂 لانه فرماندهان اسیدی",
            ]
        ),
        "defense": group_raid_service.roll_npc_target_defense(level),
        "water": group_raid_service.roll_npc_target_water(),
    }


registry.alliance_group_raid_target = alliance_group_raid_target


def alliance_group_session(al: dict[str, Any]) -> dict[str, Any] | None:
    session = al.get("group_raid_session")
    if not isinstance(session, dict):
        return None
    if registry.fromiso(session.get("expires_at"), registry.now()) <= registry.now():
        al.pop("group_raid_session", None)
        return None
    return session


registry.alliance_group_session = alliance_group_session


def alliance_group_ready_lines(
    al: dict[str, Any], session: dict[str, Any]
) -> tuple[str, int, int]:
    ready = set(session.get("ready", []))
    member_ids = [
        cid for cid in al.get("members", []) if cid in registry.game["players"]
    ]
    lines = []
    for cid in member_ids:
        mark = "✅" if cid in ready else "⬜"
        lines.append(f"{mark} {registry.player_name(cid)}")
    return ("\n".join(lines), len(ready), len(member_ids))


registry.alliance_group_ready_lines = alliance_group_ready_lines


def handle_alliance_group_raid(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if (
        al.get("group_raid_cd")
        and registry.fromiso(al.get("group_raid_cd"), registry.now()) > registry.now()
    ):
        registry.send(
            chat_id,
            registry.T(
                "alliance.group_raid_cd",
                time=registry.fmt_cd(
                    (
                        registry.fromiso(al.get("group_raid_cd"), registry.now())
                        - registry.now()
                    ).total_seconds()
                ),
            ),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    session = registry.alliance_group_session(al)
    if not session:
        target = registry.alliance_group_raid_target(al)
        session = {
            "created_at": registry.iso(registry.now()),
            "expires_at": registry.iso(registry.now() + timedelta(minutes=20)),
            "ready": [],
            "target": target,
        }
        al["group_raid_session"] = session
        registry.alliance_log(al, "group_raid_created", {"target": target.get("name")})
        registry.send_group_radio(
            registry.T(
                "group_radio.group_raid_lobby",
                alliance=al.get("name"),
                target=target.get("name"),
                total=len(
                    [
                        cid
                        for cid in al.get("members", [])
                        if cid in registry.game["players"]
                    ]
                ),
            ),
            force=True,
            reason="group_raid_lobby",
        )
    ready_lines, ready_count, total_members = registry.alliance_group_ready_lines(
        al, session
    )
    registry.save_game()
    target = session.get("target", {})
    can_start = ready_count >= total_members > 0
    rows = [[registry.B("alliance_group_ready")]]
    if can_start:
        rows.append([registry.B("alliance_group_start")])
    if al.get("owner") == chat_id:
        rows.append([registry.B("alliance_group_cancel")])
    rows.append([registry.B("alliance")])
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T(
            "alliance.group_raid_lobby",
            target=registry.display_name(target.get("name")),
            defense=registry.fmt_num(target.get("defense", 0)),
            water=registry.fmt_num(target.get("water", 0)),
            ready=ready_count,
            total=total_members,
            members=ready_lines,
            left=registry.fmt_cd(
                (
                    registry.fromiso(session.get("expires_at"), registry.now())
                    - registry.now()
                ).total_seconds()
            ),
            status=registry.T("alliance.group_raid_can_start")
            if can_start
            else registry.T("alliance.group_raid_waiting"),
        ),
        keypad=registry.make_keypad(rows),
    )


registry.handle_alliance_group_raid = handle_alliance_group_raid


def handle_alliance_group_ready(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    session = registry.alliance_group_session(al)
    if not session:
        return registry.handle_alliance_group_raid(chat_id)
    ready = session.setdefault("ready", [])
    if chat_id not in ready:
        ready.append(chat_id)
        registry.alliance_log(al, "group_raid_ready", {"player": chat_id})
    ready_count = len(set(ready))
    total_members = len(
        [cid for cid in al.get("members", []) if cid in registry.game["players"]]
    )
    if total_members > 0 and ready_count >= total_members:
        registry.send_group_radio(
            registry.T(
                "group_radio.group_raid_ready",
                alliance=al.get("name"),
                total=total_members,
            ),
            force=True,
            reason="group_raid_ready",
        )
    registry.save_game()
    registry.handle_alliance_group_raid(chat_id)


registry.handle_alliance_group_ready = handle_alliance_group_ready


def handle_alliance_group_cancel(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if al.get("owner") != chat_id:
        registry.send(
            chat_id,
            registry.T("alliance.not_owner"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    al.pop("group_raid_session", None)
    registry.alliance_log(al, "group_raid_cancelled", {"by": chat_id})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("alliance.group_raid_cancelled"),
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_alliance_group_cancel = handle_alliance_group_cancel


def handle_alliance_group_start(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    if (
        al.get("group_raid_cd")
        and registry.fromiso(al.get("group_raid_cd"), registry.now()) > registry.now()
    ):
        return registry.handle_alliance_group_raid(chat_id)
    session = registry.alliance_group_session(al)
    if not session:
        return registry.handle_alliance_group_raid(chat_id)
    member_ids = [
        cid for cid in al.get("members", []) if cid in registry.game["players"]
    ]
    ready = set(session.get("ready", []))
    if not set(member_ids).issubset(ready):
        registry.send(
            chat_id,
            registry.T("alliance.group_raid_not_all_ready"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    total_power = 0
    for cid in member_ids:
        mp = registry.game["players"][cid]
        registry.recalc_power(mp)
        total_power += int(mp.get("total_attack", 0)) + int(mp.get("level", 1)) * 25
    target = session.get("target", {})
    enemy_def = int(target.get("defense", 1000))
    effective = group_raid_service.roll_group_attack_power(total_power)
    al["group_raid_cd"] = registry.iso(registry.now() + timedelta(hours=4))
    al.pop("group_raid_session", None)
    if group_raid_service.is_group_raid_win(effective, enemy_def):
        if (
            target.get("type") == "player"
            and target.get("chat_id") in registry.game["players"]
        ):
            victim = registry.game["players"][target["chat_id"]]
            steal = group_raid_service.roll_player_target_steal(victim.get("water", 0))
            victim["water"] = max(0, int(victim.get("water", 0)) - steal)
            victim.setdefault("stats", {})["water_lost"] = (
                victim.get("stats", {}).get("water_lost", 0) + steal
            )
            registry.send(
                target["chat_id"],
                registry.T(
                    "alliance.group_raid_victim",
                    alliance=al.get("name"),
                    lost=registry.fmt_num(steal),
                ),
                keypad=registry.main_keypad(target["chat_id"]),
            )
            gross = group_raid_service.roll_player_target_gross(steal, len(member_ids))
        else:
            gross = group_raid_service.roll_npc_target_gross(
                len(member_ids), registry.cartel_level(al)
            )
        each, vault_add = group_raid_service.split_group_raid_reward(
            gross, len(member_ids)
        )
        al["vault"] = int(al.get("vault", 0)) + vault_add
        for cid in member_ids:
            mp = registry.game["players"][cid]
            mp["water"] = int(mp.get("water", 0)) + each
            mp["loot_caches"] = int(mp.get("loot_caches", 0)) + (
                1 if group_raid_service.rolls_bonus_cache() else 0
            )
            mp.setdefault("stats", {})["group_raids"] = (
                mp.get("stats", {}).get("group_raids", 0) + 1
            )
        registry.alliance_log(
            al,
            "group_raid_win",
            {
                "target": target.get("name"),
                "gross": gross,
                "vault": vault_add,
                "each": each,
            },
        )
        registry.add_news(
            registry.T(
                "alliance.group_raid_news",
                name=al.get("name"),
                target=target.get("name"),
                gross=registry.fmt_num(gross),
            ),
            important=True,
        )
        msg = registry.T(
            "alliance.group_raid_win",
            target=registry.display_name(target.get("name")),
            power=registry.fmt_num(effective),
            defense=registry.fmt_num(enemy_def),
            gross=registry.fmt_num(gross),
            each=registry.fmt_num(each),
            vault=registry.fmt_num(vault_add),
        )
    else:
        dmg = group_raid_service.roll_group_raid_loss_damage()
        for cid in member_ids:
            mp = registry.game["players"][cid]
            mp["hp"] = max(1, int(mp.get("hp", 100)) - dmg)
        registry.alliance_log(
            al, "group_raid_lose", {"target": target.get("name"), "damage": dmg}
        )
        msg = registry.T(
            "alliance.group_raid_lose",
            target=registry.display_name(target.get("name")),
            power=registry.fmt_num(effective),
            defense=registry.fmt_num(enemy_def),
            damage=dmg,
        )
    if effective < enemy_def:
        registry.send_group_radio(
            registry.T(
                "group_radio.group_raid_lost",
                alliance=al.get("name"),
                target=target.get("name"),
                power=registry.fmt_num(effective),
                defense=registry.fmt_num(enemy_def),
            ),
            force=True,
            reason="group_raid_lost",
        )
    registry.save_game()
    for cid in member_ids:
        registry.send(cid, msg, keypad=registry.alliance_keypad(cid))


registry.handle_alliance_group_start = handle_alliance_group_start
