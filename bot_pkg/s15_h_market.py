import re
from typing import Any

from .registry import registry


def handle_market_menu(chat_id: str) -> None:
    registry.maybe_system_daily_restock()
    prices = []
    for r in registry.RESOURCES:
        prices.append(
            registry.T(
                "market.price_line",
                icon=registry.RES_ICON[r],
                name=registry.RES_NAME[r],
                public=registry.system_reference_price(r),
                system=registry.system_buy_price(r),
                system_sell=registry.system_sell_price(r),
            )
        )
    registry.send(
        chat_id,
        registry.T("market.menu", prices="\n".join(prices)),
        keypad=registry.market_keypad(),
    )


registry.handle_market_menu = handle_market_menu


def open_orders() -> list[dict[str, Any]]:
    """Return currently open player market orders.

    Kept as a small helper because several market/admin screens call it.
    Missing this function caused NameError when pressing «سفارش\u200cهای من».
    """
    return [
        o
        for o in registry.game.get("market_orders", [])
        if isinstance(o, dict) and o.get("status") == "open"
    ]


registry.open_orders = open_orders


def handle_market_people(chat_id: str) -> None:
    orders = registry.open_orders()
    if not orders:
        registry.send(
            chat_id, registry.T("market.people_empty"), keypad=registry.market_keypad()
        )
        return
    lines = []
    rows: list[list[str]] = []
    for o in orders[:10]:
        r = o["resource"]
        lines.append(
            registry.T(
                "market.order_line",
                id=o["id"],
                icon=registry.RES_ICON[r],
                res_name=registry.RES_NAME[r],
                qty=o["qty"],
                unit=o["unit_price"],
                total=o["qty"] * o["unit_price"],
                seller=registry.display_name(registry.player_name(o["seller_id"])),
            )
        )
        rows.append([f"خرید #{o['id']}"])
    rows.append([registry.B("back_market"), registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T("market.people_list", id=orders[0]["id"], orders="\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_market_people = handle_market_people


def handle_create_order_prompt(chat_id: str) -> None:
    registry.game["chat_states"][chat_id] = {"state": "awaiting_market_order"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("market.create_prompt"),
        keypad=registry.make_keypad(
            [[registry.B("back_market"), registry.B("main_menu")]]
        ),
    )


registry.handle_create_order_prompt = handle_create_order_prompt


def handle_create_order(chat_id: str, text: str) -> None:
    p = registry.get_player(chat_id)
    parts = text.replace("×", " ").split()
    if len(parts) < 3:
        registry.send(
            chat_id,
            registry.T("market.bad_format")
            + "\n\n"
            + registry.T("market.create_prompt"),
            keypad=registry.market_keypad(),
        )
        return
    r = registry.res_key(parts[0])
    qty = registry.safe_int(parts[1], -1)
    unit = registry.safe_int(parts[2], -1)
    if not r:
        registry.send(
            chat_id, registry.T("market.bad_resource"), keypad=registry.market_keypad()
        )
        return
    if qty <= 0 or unit <= 0:
        registry.send(
            chat_id,
            registry.T("market.bad_format") + "\nمثال: اوراق 10 80",
            keypad=registry.market_keypad(),
        )
        return
    if p["resources"].get(r, 0) < qty:
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage({r: qty}, p)
            ),
            keypad=registry.market_keypad(),
        )
        return
    p["resources"][r] -= qty
    oid = int(registry.game.get("next_order_id", 1))
    registry.game["next_order_id"] = oid + 1
    order = {
        "id": oid,
        "seller_id": chat_id,
        "resource": r,
        "qty": qty,
        "unit_price": unit,
        "status": "open",
        "created_at": registry.iso(registry.now()),
    }
    registry.game.setdefault("market_orders", []).append(order)
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(chat_id, "market_create_order", order)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.created",
            id=oid,
            res_name=registry.RES_NAME[r],
            qty=qty,
            unit=unit,
            total=qty * unit,
        ),
        keypad=registry.market_keypad(),
    )


registry.handle_create_order = handle_create_order


def find_order(order_id: int) -> dict[str, Any] | None:
    for o in registry.game.get("market_orders", []):
        if int(o.get("id", -1)) == order_id and o.get("status") == "open":
            return o
    return None


registry.find_order = find_order


def parse_order_id(text: str) -> int | None:
    m = re.search("#?\\s*(\\d+)", text or "")
    return int(m.group(1)) if m else None


registry.parse_order_id = parse_order_id


def handle_buy_order(chat_id: str, text: str) -> None:
    oid = registry.parse_order_id(text)
    if not oid:
        registry.send(
            chat_id,
            registry.T("market.order_not_found"),
            keypad=registry.market_keypad(),
        )
        return
    o = registry.find_order(oid)
    if not o:
        registry.send(
            chat_id,
            registry.T("market.order_not_found"),
            keypad=registry.market_keypad(),
        )
        return
    if o["seller_id"] == chat_id:
        registry.send(
            chat_id,
            registry.T("market.cannot_buy_own"),
            keypad=registry.market_keypad(),
        )
        return
    buyer = registry.get_player(chat_id)
    seller = registry.get_player(o["seller_id"])
    total = int(o["qty"] * o["unit_price"])
    if buyer.get("water", 0) < total:
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_water", need=total, have=buyer.get("water", 0)
            ),
            keypad=registry.market_keypad(),
        )
        return
    buyer["water"] -= total
    buyer["resources"][o["resource"]] = buyer["resources"].get(o["resource"], 0) + int(
        o["qty"]
    )
    net, note = registry.award_water(
        o["seller_id"], total, "market_sale", alliance_share=True
    )
    o["status"] = "sold"
    o["buyer_id"] = chat_id
    o["sold_at"] = registry.iso(registry.now())
    buyer["stats"]["market_buys"] = buyer["stats"].get("market_buys", 0) + 1
    seller["stats"]["market_sales"] = seller["stats"].get("market_sales", 0) + 1
    registry.inc_mission(o["seller_id"], "market_sell", 1)
    registry.add_news(
        f"⚖️ {registry.player_name(o['seller_id'])} یک بسته در بازار فروخت: {registry.RES_NAME[o['resource']]} × {o['qty']}"
    )
    registry.log_action(chat_id, "market_buy", {"order_id": oid, "total": total})
    registry.log_action(
        o["seller_id"], "market_sold", {"order_id": oid, "gross": total, "net": net}
    )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.bought_buyer",
            seller=registry.display_name(registry.player_name(o["seller_id"])),
            res_name=registry.RES_NAME[o["resource"]],
            qty=o["qty"],
            total=total,
            water=buyer["water"],
        ),
        keypad=registry.market_keypad(),
    )
    registry.send(
        o["seller_id"],
        registry.T(
            "market.bought_seller",
            buyer=registry.player_name(chat_id),
            res_name=registry.RES_NAME[o["resource"]],
            qty=o["qty"],
            gross=total,
            net=net,
            share_note=note,
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_buy_order = handle_buy_order


def handle_my_orders(chat_id: str) -> None:
    orders = [o for o in registry.open_orders() if o["seller_id"] == chat_id]
    if not orders:
        registry.send(
            chat_id,
            registry.T("market.own_orders_empty"),
            keypad=registry.market_keypad(),
        )
        return
    lines = [
        registry.T(
            "market.order_line",
            id=o["id"],
            icon=registry.RES_ICON[o["resource"]],
            res_name=registry.RES_NAME[o["resource"]],
            qty=o["qty"],
            unit=o["unit_price"],
            total=o["qty"] * o["unit_price"],
            seller=registry.player_name(chat_id),
        )
        for o in orders
    ]
    rows = [[f"لغو #{o['id']}"] for o in orders[:10]] + [
        [registry.B("back_market"), registry.B("main_menu")]
    ]
    registry.send(
        chat_id,
        registry.T("market.own_orders", orders="\n".join(lines), id=orders[0]["id"]),
        keypad=registry.make_keypad(rows),
    )


registry.handle_my_orders = handle_my_orders


def handle_cancel_order(chat_id: str, text: str) -> None:
    oid = registry.parse_order_id(text)
    o = registry.find_order(oid or -1)
    if not o or o.get("seller_id") != chat_id:
        registry.send(
            chat_id,
            registry.T("market.order_not_found"),
            keypad=registry.market_keypad(),
        )
        return
    p = registry.get_player(chat_id)
    p["resources"][o["resource"]] = p["resources"].get(o["resource"], 0) + int(o["qty"])
    o["status"] = "cancelled"
    o["cancelled_at"] = registry.iso(registry.now())
    registry.log_action(chat_id, "market_cancel", {"order_id": oid})
    registry.save_game()
    registry.send(
        chat_id, registry.T("market.cancelled", id=oid), keypad=registry.market_keypad()
    )


registry.handle_cancel_order = handle_cancel_order


def handle_system_sell_menu(chat_id: str) -> None:
    registry.send(
        chat_id,
        registry.T("market.system_prompt"),
        keypad=registry.system_sell_keypad(),
    )


registry.handle_system_sell_menu = handle_system_sell_menu


def system_sell_resource_from_text(text: str) -> str | None:
    for r in registry.RESOURCES:
        if text == registry.B(f"system_sell_{r}"):
            return r
    return None


registry.system_sell_resource_from_text = system_sell_resource_from_text


def handle_system_sell_select(chat_id: str, r: str) -> None:
    p = registry.get_player(chat_id)
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_system_sell_qty",
        "resource": r,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.system_qty_prompt",
            res_name=registry.RES_NAME[r],
            have=p["resources"].get(r, 0),
            price=registry.system_buy_price(r),
        ),
        keypad=registry.make_keypad(
            [["همه"], [registry.B("back_market"), registry.B("main_menu")]]
        ),
    )


registry.handle_system_sell_select = handle_system_sell_select


def handle_system_sell_qty(chat_id: str, text: str) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    r = st.get("resource")
    if r not in registry.RESOURCES:
        registry.game["chat_states"].pop(chat_id, None)
        registry.handle_market_menu(chat_id)
        return
    p = registry.get_player(chat_id)
    have = int(p["resources"].get(r, 0))
    qty = have if text.strip() == "همه" else registry.safe_int(text, -1)
    if qty <= 0 or qty > have:
        registry.send(
            chat_id,
            registry.T("errors.bad_number"),
            keypad=registry.system_sell_keypad(),
        )
        return
    price = registry.system_buy_price(r)
    gross = qty * price
    p["resources"][r] -= qty
    registry.game.setdefault("market_supply", {})[r] = (
        int(registry.game.get("market_supply", {}).get(r, 0)) + qty
    )
    net, note = registry.award_water(chat_id, gross, "system_sale", alliance_share=True)
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(
        chat_id, "system_sell", {"resource": r, "qty": qty, "gross": gross, "net": net}
    )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.system_sold",
            res_name=registry.RES_NAME[r],
            qty=qty,
            price=price,
            gross=gross,
            net=net,
            share_note=note,
        ),
        keypad=registry.market_keypad(),
    )


registry.handle_system_sell_qty = handle_system_sell_qty


def handle_system_buy_menu(chat_id: str) -> None:
    registry.maybe_system_daily_restock()
    supply = registry.game.setdefault("market_supply", {})
    lines = []
    for r in registry.RESOURCES:
        lines.append(
            registry.T(
                "market.system_buy_line",
                icon=registry.RES_ICON[r],
                res_name=registry.RES_NAME[r],
                price=registry.system_sell_price(r),
                available=int(supply.get(r, 0)),
            )
        )
    registry.send(
        chat_id,
        registry.T(
            "market.system_buy_prompt",
            items="\n".join(lines),
            hour=registry.DAILY_EVENT_HOUR,
            daily_scrap=registry.SYSTEM_DAILY_RESTOCK["scrap"],
            daily_plastic=registry.SYSTEM_DAILY_RESTOCK["plastic"],
            daily_glass=registry.SYSTEM_DAILY_RESTOCK["glass"],
            daily_battery=registry.SYSTEM_DAILY_RESTOCK["battery"],
            daily_copper=registry.SYSTEM_DAILY_RESTOCK["copper"],
        ),
        keypad=registry.system_buy_keypad(),
    )


registry.handle_system_buy_menu = handle_system_buy_menu


def system_buy_resource_from_text(text: str) -> str | None:
    for r in registry.RESOURCES:
        if text == registry.B(f"system_buy_{r}"):
            return r
    return None


registry.system_buy_resource_from_text = system_buy_resource_from_text


def handle_system_buy_select(chat_id: str, r: str) -> None:
    supply = int(registry.game.setdefault("market_supply", {}).get(r, 0))
    if supply <= 0:
        registry.send(
            chat_id,
            registry.T("market.system_buy_empty", res_name=registry.RES_NAME[r]),
            keypad=registry.system_buy_keypad(),
        )
        return
    p = registry.get_player(chat_id)
    price = registry.system_sell_price(r)
    water = int(p.get("water", 0))
    max_buy = min(supply, water // price)
    if max_buy <= 0:
        registry.send(
            chat_id,
            registry.T("errors.not_enough_water", need=price, have=water),
            keypad=registry.system_buy_keypad(),
        )
        return
    registry.game["chat_states"][chat_id] = {
        "state": "awaiting_system_buy_qty",
        "resource": r,
    }
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.system_buy_qty_prompt",
            res_name=registry.RES_NAME[r],
            available=supply,
            price=price,
            water=water,
            max_buy=max_buy,
        ),
        keypad=registry.make_keypad(
            [["حداکثر"], [registry.B("back_market"), registry.B("main_menu")]]
        ),
    )


registry.handle_system_buy_select = handle_system_buy_select


def handle_system_buy_qty(chat_id: str, text: str) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    r = st.get("resource")
    if r not in registry.RESOURCES:
        registry.game["chat_states"].pop(chat_id, None)
        registry.handle_market_menu(chat_id)
        return
    p = registry.get_player(chat_id)
    supply = int(registry.game.setdefault("market_supply", {}).get(r, 0))
    price = registry.system_sell_price(r)
    max_buy = min(supply, int(p.get("water", 0)) // price)
    wants_max = text.strip() in {"حداکثر", "همه"}
    qty = max_buy if wants_max else registry.safe_int(text, -1)
    if qty <= 0:
        if wants_max:
            registry.send(
                chat_id,
                registry.T(
                    "errors.not_enough_water", need=price, have=int(p.get("water", 0))
                ),
                keypad=registry.system_buy_keypad(),
            )
        else:
            registry.send(
                chat_id,
                registry.T("errors.bad_number"),
                keypad=registry.system_buy_keypad(),
            )
        return
    if supply <= 0:
        registry.game["chat_states"].pop(chat_id, None)
        registry.send(
            chat_id,
            registry.T("market.system_buy_empty", res_name=registry.RES_NAME[r]),
            keypad=registry.market_keypad(),
        )
        return
    if qty > supply:
        registry.send(
            chat_id,
            registry.T(
                "market.system_buy_not_enough_supply",
                res_name=registry.RES_NAME[r],
                available=supply,
            ),
            keypad=registry.system_buy_keypad(),
        )
        return
    total = qty * price
    if int(p.get("water", 0)) < total:
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_water", need=total, have=int(p.get("water", 0))
            ),
            keypad=registry.system_buy_keypad(),
        )
        return
    p["water"] = int(p.get("water", 0)) - total
    p["resources"][r] = int(p["resources"].get(r, 0)) + qty
    registry.game["market_supply"][r] = supply - qty
    p.setdefault("stats", {})["market_buys"] = (
        int(p.get("stats", {}).get("market_buys", 0)) + 1
    )
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(
        chat_id,
        "system_buy",
        {"resource": r, "qty": qty, "price": price, "total": total},
    )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "market.system_bought",
            res_name=registry.RES_NAME[r],
            qty=qty,
            price=price,
            total=total,
            water=int(p.get("water", 0)),
        ),
        keypad=registry.market_keypad(),
    )


registry.handle_system_buy_qty = handle_system_buy_qty
