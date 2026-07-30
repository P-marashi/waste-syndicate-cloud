from ..registry import registry


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
