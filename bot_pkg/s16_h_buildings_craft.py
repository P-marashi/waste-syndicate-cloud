from datetime import timedelta
from typing import Any

from .registry import registry
from .services import building_service


def building_effect_text(data: dict[str, Any]) -> str:
    parts = []
    if data.get("prod"):
        parts.append(f"تولید {data['prod']}💧/ساعت")
    if data.get("def"):
        parts.append(f"دفاع +{data['def']}")
    if data.get("atk"):
        parts.append(f"حمله +{data['atk']}")
    if data.get("discount"):
        parts.append(f"تخفیف ساخت {int(data['discount'] * 100)}٪")
    if data.get("fee_cut"):
        parts.append(f"کاهش هزینه بازار {int(data['fee_cut'] * 100)}٪")
    if data.get("heal_bonus"):
        parts.append(f"درمان +{data['heal_bonus']}")
    return " | ".join(parts) or "اثر ویژه"


registry.building_effect_text = building_effect_text


def buildings_keypad() -> dict[str, Any]:
    rows = [[f"⬆️ {data['label']}"] for data in registry.BUILDINGS.values()]
    rows.append([registry.B("main_menu")])
    return registry.make_keypad(rows)


registry.buildings_keypad = buildings_keypad


def handle_buildings_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    finished = registry.finish_upgrades(p)
    lines = []
    for bk, bdata in registry.BUILDINGS.items():
        lv = int(p.get("buildings", {}).get(bk, 0))
        inprog = registry.upgrade_in_progress(p, bk)
        max_lv = max(bdata["levels"].keys())
        if inprog is not None:
            status = registry.T("buildings.progress", time=registry.fmt_cd(inprog))
        elif lv <= 0:
            status = registry.T("buildings.not_built")
        elif lv >= max_lv:
            status = registry.T("buildings.max", level=lv)
        else:
            status = registry.T("buildings.level", level=lv)
        if lv >= max_lv:
            next_info = "سقف فعلی"
        else:
            nd = bdata["levels"][lv + 1]
            next_info = registry.T(
                "buildings.next_info",
                cost=registry.fmt_res_dict(nd["cost"]),
                time=registry.fmt_cd(nd["time"]),
                effect=registry.building_effect_text(nd),
            )
        lines.append(
            registry.T(
                "buildings.line",
                label=bdata["label"],
                status=status,
                next_info=next_info,
            )
        )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("buildings.menu", lines="\n".join(lines)),
        keypad=registry.buildings_keypad(),
    )


registry.handle_buildings_menu = handle_buildings_menu


def handle_building_detail(chat_id: str, bk: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    bd = registry.BUILDINGS[bk]
    lv = int(p.get("buildings", {}).get(bk, 0))
    max_lv = max(bd["levels"].keys())

    # Store last building in chat state for upgrade
    registry.chat_state_repo.save(chat_id, {
        "state": "building_detail",
        "last_building": bk,
    })

    # Get current level's production/effect
    current_effect = ""
    if lv > 0 and lv in bd["levels"]:
        nd = bd["levels"][lv]
        current_effect = registry.building_effect_text(nd)

    inprog = registry.upgrade_in_progress(p, bk)

    if lv <= 0:
        status_line = f"❌ ساخته نشده"
    elif inprog is not None:
        status_line = f"🔄 در حال ارتقا: {registry.fmt_cd(inprog)}"
    elif lv >= max_lv:
        status_line = f"✅ حداکثر سطح ({lv})"
    else:
        status_line = f"📊 سطح فعلی: {lv}"

    text = f"""{registry.B(bk)}
━━━━━━━━━━━━
{bd['desc']}
{status_line}
اثر فعلی: {current_effect}
━━━━━━━━━━━━"""

    keypad_rows = []

    if lv < max_lv and inprog is None:
        nd = bd["levels"][lv + 1]
        cost = dict(nd["cost"])
        discount = building_service.lab_discount_rate(
            p.get("buildings", {}), registry.BUILDINGS["lab"]["levels"], exclude_key=bk
        )
        if discount:
            cost = building_service.apply_discount(cost, discount)

        can_upgrade = registry.has_resources(p, cost)
        upgrade_btn = f"⬆️ ارتقا به سطح {lv + 1}"
        if can_upgrade:
            keypad_rows.append([upgrade_btn])
        else:
            keypad_rows.append([f"{upgrade_btn} ❌ کمبود منابع"])

        text += f"""
📈 ارتقا به سطح {lv + 1}:
{registry.fmt_res_lines(cost)}
⏱️ زمان: {registry.fmt_cd(nd["time"])}
اثر جدید: {registry.building_effect_text(nd)}"""
    elif inprog is not None:
        text += f"\n⏳ زمان باقی‌مانده: {registry.fmt_cd(inprog)}"

    keypad_rows.append([registry.B("buildings"), registry.B("main_menu")])
    registry.save_game()
    registry.send(chat_id, text, keypad=registry.make_keypad(keypad_rows))


registry.handle_building_detail = handle_building_detail


def building_key_from_text(text: str) -> str | None:
    # Direct button match (new style with emoji)
    for bk in registry.BUILDINGS:
        if text == registry.B(bk):
            return bk
    # Old style match
    for bk, bd in registry.BUILDINGS.items():
        if text == f"⬆️ {bd['label']}":
            return bk
    return None


registry.building_key_from_text = building_key_from_text


def handle_upgrade(chat_id: str, bk: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    bd = registry.BUILDINGS[bk]
    lv = int(p.get("buildings", {}).get(bk, 0))
    max_lv = max(bd["levels"].keys())
    if lv >= max_lv:
        registry.send(
            chat_id,
            registry.T("buildings.maxed", label=bd["label"]),
            keypad=registry.buildings_keypad(),
        )
        return
    inprog = registry.upgrade_in_progress(p, bk)
    if inprog is not None:
        registry.send(
            chat_id,
            registry.T(
                "buildings.already_progress",
                label=bd["label"],
                time=registry.fmt_cd(inprog),
            ),
            keypad=registry.buildings_keypad(),
        )
        return
    nd = bd["levels"][lv + 1]
    cost = dict(nd["cost"])
    discount = building_service.lab_discount_rate(
        p.get("buildings", {}), registry.BUILDINGS["lab"]["levels"], exclude_key=bk
    )
    if discount:
        cost = building_service.apply_discount(cost, discount)
    if not registry.has_resources(p, cost):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(cost, p)
            ),
            keypad=registry.buildings_keypad(),
        )
        return
    registry.pay_cost(p, cost)
    finish = registry.iso(registry.now() + timedelta(seconds=nd["time"]))
    p.setdefault("upgrades_in_progress", []).append(
        {"bldg": bk, "to_level": lv + 1, "finish": finish}
    )
    registry.log_action(
        chat_id, "upgrade_start", {"building": bk, "level": lv + 1, "cost": cost}
    )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "buildings.upgrade_started",
            label=bd["label"],
            level=lv + 1,
            cost=registry.fmt_res_lines(cost),
            time=registry.fmt_cd(nd["time"]),
        ),
        keypad=registry.buildings_keypad(),
    )
    registry.apply_building_bonuses(p)
    registry.recalc_power(p)


registry.handle_upgrade = handle_upgrade


def craft_keypad() -> dict[str, Any]:
    rows = [[item["label"]] for item in registry.CRAFT_ITEMS.values()]
    rows.append([registry.B("main_menu")])
    return registry.make_keypad(rows)


registry.craft_keypad = craft_keypad


def buildings_keypad() -> dict[str, Any]:
    rows = [
        [registry.B("purifier"), registry.B("wall")],
        [registry.B("armory"), registry.B("laboratory")],
        [registry.B("clinic")],
        [registry.B("main_menu")],
    ]
    return registry.make_keypad(rows)


def craft_key_from_text(text: str) -> str | None:
    for k, item in registry.CRAFT_ITEMS.items():
        if text == item["label"]:
            return k
    return None


registry.craft_key_from_text = craft_key_from_text


def discounted_craft_cost(p: dict[str, Any], cost: dict[str, int]) -> dict[str, int]:
    rate = building_service.craft_discount_rate(
        p.get("buildings", {}),
        registry.BUILDINGS["lab"]["levels"],
        event_discount=registry.event_mod("craft_discount", 0.0),
    )
    return building_service.apply_discount(cost, rate)


registry.discounted_craft_cost = discounted_craft_cost


def handle_craft_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    lines = []
    for k, item in registry.CRAFT_ITEMS.items():
        cost = registry.discounted_craft_cost(p, item["cost"])
        effect = []
        if item.get("atk"):
            effect.append(f"⚔️ حمله +{item['atk']}")
        if item.get("def"):
            effect.append(f"🛡️ دفاع +{item['def']}")
        if item.get("heal"):
            effect.append(f"❤️ جان +{item['heal']}")
        if item.get("special"):
            effect.append(registry.SPECIAL_EFFECT_TEXT.get(k, "✨ آیتم خاص"))
        lines.append(
            registry.T(
                "craft.line",
                label=item["label"],
                cost=registry.fmt_res_dict(cost),
                effect=" | ".join(effect),
            )
        )
    registry.send(
        chat_id,
        registry.T("craft.menu", lines="\n".join(lines)),
        keypad=registry.craft_keypad(),
    )


registry.handle_craft_menu = handle_craft_menu


def handle_craft(chat_id: str, item_key: str) -> None:
    p = registry.get_player(chat_id)
    item = registry.CRAFT_ITEMS[item_key]
    cost = registry.discounted_craft_cost(p, item["cost"])
    if not registry.has_resources(p, cost):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(cost, p)
            ),
            keypad=registry.craft_keypad(),
        )
        return
    spec = item.get("special")
    if spec == "repair" and (not p.get("upgrades_in_progress")):
        registry.send(
            chat_id,
            "🔧 الان هیچ ارتقایی در جریان نداری.\n\nکیت تعمیر وقتی به درد می\u200cخورد که یک ساختمان در حال ارتقا باشد.",
            keypad=registry.craft_keypad(),
        )
        return
    if spec == "shield" and registry.is_shielded(p):
        registry.send(
            chat_id,
            registry.T(
                "shield.active", time=registry.fmt_cd(registry.shield_remaining(p))
            ),
            keypad=registry.craft_keypad(),
        )
        return
    registry.pay_cost(p, cost)
    if spec == "shield":
        if registry.is_shielded(p):
            registry.send(
                chat_id,
                registry.T(
                    "shield.active", time=registry.fmt_cd(registry.shield_remaining(p))
                ),
                keypad=registry.craft_keypad(),
            )
            return
        p["shield_until"] = registry.iso(
            registry.now()
            + timedelta(seconds=int(item.get("duration", registry.SHIELD_DURATION)))
        )
        msg = registry.T(
            "craft.shield_activated",
            time=registry.fmt_cd(int(item.get("duration", registry.SHIELD_DURATION))),
        )
    elif spec == "repair":
        for u in p.get("upgrades_in_progress", []):
            finish = registry.fromiso(u.get("finish"), registry.now())
            left = max(0, (finish - registry.now()).total_seconds())
            u["finish"] = registry.iso(
                registry.now()
                + timedelta(seconds=building_service.halve_remaining_seconds(left))
            )
        msg = registry.T("craft.repair")
    elif spec:
        p.setdefault("inventory", {})[item_key] = (
            p.get("inventory", {}).get(item_key, 0) + 1
        )
        msg = registry.T(
            "craft.special", label=item["label"], qty=p["inventory"][item_key]
        )
    elif item.get("heal"):
        heal_bonus = 0
        h_lv = int(p.get("buildings", {}).get("hospital", 0))
        if h_lv:
            heal_bonus = (
                registry.BUILDINGS["hospital"]["levels"]
                .get(h_lv, {})
                .get("heal_bonus", 0)
            )
        heal, new_hp = building_service.compute_heal(
            p.get("hp", 100), item["heal"], heal_bonus=heal_bonus
        )
        p["hp"] = new_hp
        msg = registry.T("craft.healed", label=item["label"], heal=heal, hp=p["hp"])
    else:
        p.setdefault("inventory", {})[item_key] = (
            p.get("inventory", {}).get(item_key, 0) + 1
        )
        registry.recalc_power(p)
        msg = registry.T(
            "craft.crafted",
            label=item["label"],
            attack=f"{p['total_attack']:,}",
            defense=f"{p['total_defense']:,}",
        )
    registry.log_action(chat_id, "craft", {"item": item_key, "cost": cost})
    registry.save_game()
    registry.send(chat_id, msg, keypad=registry.craft_keypad())


registry.handle_craft = handle_craft
