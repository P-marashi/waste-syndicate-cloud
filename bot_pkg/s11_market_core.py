import re
from datetime import timedelta
from typing import Any

from .registry import registry


def system_reference_price(res: str) -> int:
    base = registry.BASE_PRICE[res]
    supply = max(0, int(registry.game.get("market_supply", {}).get(res, 0)))
    price = int(base * 1.05 - min(base * 0.35, supply * 0.25))
    price = max(int(base * 0.65), min(price, int(base * 1.8)))
    price = int(price * registry.event_mod("all_prices", 1.0))
    price = int(price * registry.event_mod(f"price_{res}", 1.0))
    return max(1, price)


registry.system_reference_price = system_reference_price


def system_buy_price(res: str) -> int:
    return max(1, int(registry.system_reference_price(res) * 0.25))


registry.system_buy_price = system_buy_price


def system_sell_price(res: str) -> int:
    return max(1, int(registry.system_reference_price(res) * 2.5))


registry.system_sell_price = system_sell_price


def maybe_system_daily_restock() -> bool:
    """
    روزی یک بار مقدار کمی موجودی اضطراری به سیستم اضافه می\u200cکند.
    این شارژ بی\u200cنهایت نیست: فقط تا سقف تعیین\u200cشده پر می\u200cشود.
    موجودی\u200cای که بازیکن\u200cها با «فروش فوری به سیستم» اضافه می\u200cکنند، جداگانه باقی می\u200cماند.
    """
    today = registry.today_key()
    if registry.game.get("last_system_restock") == today:
        return False
    if registry.now().hour < registry.DAILY_EVENT_HOUR:
        return False
    supply = registry.game.setdefault(
        "market_supply", {r: 0 for r in registry.RESOURCES}
    )
    added: dict[str, int] = {}
    for r in registry.RESOURCES:
        current = max(0, int(supply.get(r, 0)))
        daily = max(0, int(registry.SYSTEM_DAILY_RESTOCK.get(r, 0)))
        cap = max(daily, int(registry.SYSTEM_STOCK_CAP.get(r, daily)))
        qty = max(0, min(daily, cap - current))
        if qty > 0:
            supply[r] = current + qty
            added[r] = qty
        else:
            supply[r] = current
    registry.game["last_system_restock"] = today
    if added:
        log = registry.game.setdefault("system_stock_log", [])
        log.append({"date": today, "added": added})
        del log[:-30]
    registry.save_game()
    return bool(added)


registry.maybe_system_daily_restock = maybe_system_daily_restock


def market_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("market_people"), registry.B("market_create_order")],
            [registry.B("market_my_orders"), registry.B("market_barter")],
            [registry.B("market_my_barters"), registry.B("market_resource_rentals")],
            [registry.B("market_system_sell"), registry.B("market_system_buy")],
            [registry.B("market_prices")],
            [registry.B("main_menu")],
        ]
    )


registry.market_keypad = market_keypad


def system_sell_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("system_sell_scrap"), registry.B("system_sell_plastic")],
            [registry.B("system_sell_glass"), registry.B("system_sell_battery")],
            [registry.B("system_sell_copper")],
            [registry.B("back_market"), registry.B("main_menu")],
        ]
    )


registry.system_sell_keypad = system_sell_keypad


def system_buy_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("system_buy_scrap"), registry.B("system_buy_plastic")],
            [registry.B("system_buy_glass"), registry.B("system_buy_battery")],
            [registry.B("system_buy_copper")],
            [registry.B("back_market"), registry.B("main_menu")],
        ]
    )


registry.system_buy_keypad = system_buy_keypad


def open_barter_orders() -> list[dict[str, Any]]:
    registry.expire_barter_orders()
    return [
        o for o in registry.game.get("barter_orders", []) if o.get("status") == "open"
    ]


registry.open_barter_orders = open_barter_orders


def parse_resource_pairs(text: str) -> dict[str, int] | None:
    if not text:
        return None
    tokens = re.findall("[\\wآ-یئ]+|\\d+", text.replace("×", " ").replace("،", " "))
    result: dict[str, int] = {}
    i = 0
    while i < len(tokens):
        r = registry.res_key(tokens[i])
        if not r or r == "water" or r not in registry.RESOURCES:
            return None
        if i + 1 >= len(tokens):
            return None
        qty = registry.safe_int(tokens[i + 1], -1)
        if qty <= 0:
            return None
        result[r] = result.get(r, 0) + qty
        i += 2
    return result or None


registry.parse_resource_pairs = parse_resource_pairs


def parse_barter_text(text: str) -> tuple[dict[str, int], dict[str, int]] | None:
    if "=" not in text:
        return None
    left, right = text.split("=", 1)
    give = registry.parse_resource_pairs(left)
    want = registry.parse_resource_pairs(right)
    if not give or not want:
        return None
    return (give, want)


registry.parse_barter_text = parse_barter_text


def expire_barter_orders() -> None:
    changed = False
    now_ts = registry.now()
    for o in registry.game.setdefault("barter_orders", []):
        if o.get("status") != "open":
            continue
        expires_at = registry.fromiso(o.get("expires_at"), now_ts)
        if expires_at > now_ts:
            continue
        seller = registry.game.get("players", {}).get(o.get("seller_id"))
        if seller:
            for r, q in o.get("give", {}).items():
                registry.add_amount(seller, r, int(q))
        o["status"] = "expired"
        o["expired_at"] = registry.iso(now_ts)
        changed = True
    if changed:
        registry.save_game()


registry.expire_barter_orders = expire_barter_orders


def handle_barter_menu(chat_id: str) -> None:
    orders = [o for o in registry.open_barter_orders() if o.get("seller_id") != chat_id]
    if not orders:
        rows = [
            [registry.B("market_create_barter")],
            [registry.B("market_my_barters")],
            [registry.B("back_market"), registry.B("main_menu")],
        ]
        registry.send(
            chat_id, registry.T("barter.empty"), keypad=registry.make_keypad(rows)
        )
        return
    lines = []
    rows: list[list[str]] = []
    for o in orders[:10]:
        lines.append(
            registry.T(
                "barter.order_line",
                id=o["id"],
                seller=registry.display_name(registry.player_name(o["seller_id"])),
                give=registry.fmt_res_dict(o.get("give", {})),
                want=registry.fmt_res_dict(o.get("want", {})),
                left=registry.fmt_cd(
                    (
                        registry.fromiso(o.get("expires_at"), registry.now())
                        - registry.now()
                    ).total_seconds()
                ),
            )
        )
        rows.append([f"قبول معاوضه #{o['id']}"])
    rows.append([registry.B("market_create_barter"), registry.B("market_my_barters")])
    rows.append([registry.B("back_market"), registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T("barter.list", orders="\n\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_barter_menu = handle_barter_menu


def handle_create_barter_prompt(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    active = [o for o in registry.open_barter_orders() if o.get("seller_id") == chat_id]
    if len(active) >= 3:
        registry.send(
            chat_id, registry.T("barter.too_many"), keypad=registry.market_keypad()
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_barter_order"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("barter.create_prompt"),
        keypad=registry.make_keypad(
            [[registry.B("back_market"), registry.B("main_menu")]]
        ),
    )


registry.handle_create_barter_prompt = handle_create_barter_prompt


def handle_create_barter(chat_id: str, text: str) -> None:
    p = registry.get_player(chat_id)
    parsed = registry.parse_barter_text(text)
    if not parsed:
        registry.send(
            chat_id, registry.T("barter.bad_format"), keypad=registry.market_keypad()
        )
        return
    give, want = parsed
    active = [o for o in registry.open_barter_orders() if o.get("seller_id") == chat_id]
    if len(active) >= 3:
        registry.send(
            chat_id, registry.T("barter.too_many"), keypad=registry.market_keypad()
        )
        return
    if not registry.has_resources(p, give):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(give, p)
            ),
            keypad=registry.market_keypad(),
        )
        return
    registry.pay_cost(p, give)
    oid = int(registry.game.get("next_barter_id", 1))
    registry.game["next_barter_id"] = oid + 1
    order = {
        "id": oid,
        "seller_id": chat_id,
        "give": give,
        "want": want,
        "status": "open",
        "created_at": registry.iso(registry.now()),
        "expires_at": registry.iso(registry.now() + timedelta(hours=12)),
    }
    registry.game.setdefault("barter_orders", []).append(order)
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(chat_id, "barter_create", order)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "barter.created",
            id=oid,
            give=registry.fmt_res_dict(give),
            want=registry.fmt_res_dict(want),
        ),
        keypad=registry.market_keypad(),
    )


registry.handle_create_barter = handle_create_barter


def find_barter_order(barter_id: int) -> dict[str, Any] | None:
    for o in registry.open_barter_orders():
        if int(o.get("id", -1)) == int(barter_id):
            return o
    return None


registry.find_barter_order = find_barter_order


def handle_accept_barter(chat_id: str, text: str) -> None:
    oid = registry.parse_order_id(text)
    o = registry.find_barter_order(oid or -1)
    if not o:
        registry.send(
            chat_id, registry.T("barter.not_found"), keypad=registry.market_keypad()
        )
        return
    if o.get("seller_id") == chat_id:
        registry.send(
            chat_id,
            registry.T("barter.cannot_accept_own"),
            keypad=registry.market_keypad(),
        )
        return
    buyer = registry.get_player(chat_id)
    seller = registry.get_player(o["seller_id"])
    want = o.get("want", {})
    give = o.get("give", {})
    if not registry.has_resources(buyer, want):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(want, buyer)
            ),
            keypad=registry.market_keypad(),
        )
        return
    registry.pay_cost(buyer, want)
    for r, q in give.items():
        registry.add_amount(buyer, r, int(q))
    for r, q in want.items():
        registry.add_amount(seller, r, int(q))
    o["status"] = "done"
    o["buyer_id"] = chat_id
    o["done_at"] = registry.iso(registry.now())
    buyer.setdefault("stats", {})["barter_done"] = (
        int(buyer.get("stats", {}).get("barter_done", 0)) + 1
    )
    seller.setdefault("stats", {})["barter_done"] = (
        int(seller.get("stats", {}).get("barter_done", 0)) + 1
    )
    registry.inc_mission(chat_id, "barter", 1)
    registry.inc_mission(o["seller_id"], "barter", 1)
    registry.inc_mission(chat_id, "market_sell", 1)
    registry.inc_mission(o["seller_id"], "market_sell", 1)
    registry.log_action(chat_id, "barter_accept", {"id": oid})
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "barter.accepted_buyer",
            give=registry.fmt_res_dict(want),
            got=registry.fmt_res_dict(give),
            seller=registry.display_name(registry.player_name(o["seller_id"])),
        ),
        keypad=registry.market_keypad(),
    )
    registry.send(
        o["seller_id"],
        registry.T(
            "barter.accepted_seller",
            give=registry.fmt_res_dict(give),
            got=registry.fmt_res_dict(want),
            buyer=registry.display_name(registry.player_name(chat_id)),
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_accept_barter = handle_accept_barter


def handle_my_barters(chat_id: str) -> None:
    registry.expire_barter_orders()
    orders = [
        o
        for o in registry.game.get("barter_orders", [])
        if o.get("seller_id") == chat_id and o.get("status") == "open"
    ]
    if not orders:
        registry.send(
            chat_id, registry.T("barter.my_empty"), keypad=registry.market_keypad()
        )
        return
    lines = [
        registry.T(
            "barter.my_line",
            id=o["id"],
            give=registry.fmt_res_dict(o.get("give", {})),
            want=registry.fmt_res_dict(o.get("want", {})),
            left=registry.fmt_cd(
                (
                    registry.fromiso(o.get("expires_at"), registry.now())
                    - registry.now()
                ).total_seconds()
            ),
        )
        for o in orders
    ]
    rows = [[f"لغو معاوضه #{o['id']}"] for o in orders[:10]] + [
        [registry.B("market_create_barter")],
        [registry.B("back_market"), registry.B("main_menu")],
    ]
    registry.send(
        chat_id,
        registry.T("barter.my_list", orders="\n\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_my_barters = handle_my_barters


def handle_cancel_barter(chat_id: str, text: str) -> None:
    oid = registry.parse_order_id(text)
    o = registry.find_barter_order(oid or -1)
    if not o or o.get("seller_id") != chat_id:
        registry.send(
            chat_id, registry.T("barter.not_found"), keypad=registry.market_keypad()
        )
        return
    p = registry.get_player(chat_id)
    for r, q in o.get("give", {}).items():
        registry.add_amount(p, r, int(q))
    o["status"] = "cancelled"
    o["cancelled_at"] = registry.iso(registry.now())
    registry.log_action(chat_id, "barter_cancel", {"id": oid})
    registry.save_game()
    registry.send(
        chat_id, registry.T("barter.cancelled", id=oid), keypad=registry.market_keypad()
    )


registry.handle_cancel_barter = handle_cancel_barter


def open_rental_contracts() -> list[dict[str, Any]]:
    registry.process_resource_rentals()
    return [
        x
        for x in registry.game.get("resource_rentals", [])
        if x.get("status") == "open"
    ]


registry.open_rental_contracts = open_rental_contracts


def parse_rental_text(text: str) -> tuple[dict[str, int], dict[str, int], int] | None:
    if "=" not in text:
        return None
    left, right = text.split("=", 1)
    right_tokens = right.split()
    hours = 6
    if right_tokens and registry.safe_int(right_tokens[-1], -1) > 0:
        hours = registry.safe_int(right_tokens[-1], 6)
        right = " ".join(right_tokens[:-1])
    give = registry.parse_resource_pairs(left)
    repay = registry.parse_resource_pairs(right)
    if not give or not repay:
        return None
    hours = max(1, min(48, int(hours)))
    return (give, repay, hours * 3600)


registry.parse_rental_text = parse_rental_text


def rental_profit_ok(give: dict[str, int], repay: dict[str, int]) -> bool:
    if len(give) == 1 and len(repay) == 1:
        rg, qg = next(iter(give.items()))
        rr, qr = next(iter(repay.items()))
        if rg == rr and int(qr) > int(qg * 1.3 + 0.999):
            return False
    return True


registry.rental_profit_ok = rental_profit_ok


def player_has_active_rental(chat_id: str) -> bool:
    for c in registry.game.get("resource_rentals", []):
        if c.get("status") in {"accepted", "overdue"} and (
            c.get("borrower") == chat_id or c.get("lender") == chat_id
        ):
            return True
    return False


registry.player_has_active_rental = player_has_active_rental


def process_resource_rentals() -> None:
    changed = False
    now_ts = registry.now()
    for c in registry.game.setdefault("resource_rentals", []):
        if c.get("status") not in {"accepted", "overdue"}:
            continue
        borrower = registry.game.get("players", {}).get(c.get("borrower"))
        lender = registry.game.get("players", {}).get(c.get("lender"))
        if not borrower or not lender:
            continue
        if registry.fromiso(c.get("due_at"), now_ts) <= now_ts:
            c["status"] = "overdue"
            changed = True
        if c.get("status") == "overdue":
            remaining = c.setdefault("remaining", dict(c.get("repay", {})))
            for r, need in list(remaining.items()):
                take = min(int(need), registry.amount_of(borrower, r))
                if take > 0:
                    registry.add_amount(borrower, r, -take)
                    registry.add_amount(lender, r, take)
                    remaining[r] = int(need) - take
                    changed = True
                if int(remaining.get(r, 0)) <= 0:
                    remaining.pop(r, None)
            if not remaining:
                c["status"] = "repaid"
                c["repaid_at"] = registry.iso(now_ts)
                changed = True
    if changed:
        registry.save_game()


registry.process_resource_rentals = process_resource_rentals


def rental_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("rental_create"), registry.B("rental_my")],
            [registry.B("back_market"), registry.B("main_menu")],
        ]
    )


registry.rental_keypad = rental_keypad


def handle_resource_rentals(chat_id: str) -> None:
    contracts = [
        c for c in registry.open_rental_contracts() if c.get("lender") != chat_id
    ]
    lines = []
    rows: list[list[str]] = []
    for c in contracts[:10]:
        lines.append(
            registry.T(
                "rental.line",
                id=c["id"],
                lender=registry.display_name(registry.player_name(c["lender"])),
                give=registry.fmt_res_dict(c.get("give", {})),
                repay=registry.fmt_res_dict(c.get("repay", {})),
                time=registry.fmt_cd(int(c.get("duration_seconds", 0))),
            )
        )
        rows.append([f"قبول قرارداد #{c['id']}"])
    rows.append([registry.B("rental_create"), registry.B("rental_my")])
    rows.append([registry.B("back_market"), registry.B("main_menu")])
    txt = registry.T(
        "rental.list",
        contracts="\n\n".join(lines) if lines else registry.T("rental.empty"),
    )
    registry.send(chat_id, txt, keypad=registry.make_keypad(rows))


registry.handle_resource_rentals = handle_resource_rentals


def handle_create_rental_prompt(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    if int(p.get("level", 1)) < 3:
        registry.send(
            chat_id,
            registry.T("rental.level_required"),
            keypad=registry.market_keypad(),
        )
        return
    if registry.player_has_active_rental(chat_id):
        registry.send(
            chat_id, registry.T("rental.active_limit"), keypad=registry.market_keypad()
        )
        return
    registry.game["chat_states"][chat_id] = {"state": "awaiting_rental_order"}
    registry.save_game()
    registry.send(
        chat_id,
        registry.T("rental.create_prompt"),
        keypad=registry.make_keypad(
            [[registry.B("back_market"), registry.B("main_menu")]]
        ),
    )


registry.handle_create_rental_prompt = handle_create_rental_prompt


def handle_create_rental(chat_id: str, text: str) -> None:
    p = registry.get_player(chat_id)
    parsed = registry.parse_rental_text(text)
    if not parsed:
        registry.send(
            chat_id, registry.T("rental.bad_format"), keypad=registry.market_keypad()
        )
        return
    give, repay, duration = parsed
    if not registry.rental_profit_ok(give, repay):
        registry.send(
            chat_id, registry.T("rental.profit_limit"), keypad=registry.market_keypad()
        )
        return
    if not registry.has_resources(p, give):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(give, p)
            ),
            keypad=registry.market_keypad(),
        )
        return
    registry.pay_cost(p, give)
    cid = int(registry.game.get("next_rental_id", 1))
    registry.game["next_rental_id"] = cid + 1
    c = {
        "id": cid,
        "lender": chat_id,
        "borrower": None,
        "give": give,
        "repay": repay,
        "duration_seconds": duration,
        "accepted_at": None,
        "due_at": None,
        "status": "open",
        "created_at": registry.iso(registry.now()),
    }
    registry.game.setdefault("resource_rentals", []).append(c)
    registry.game["chat_states"].pop(chat_id, None)
    registry.log_action(chat_id, "rental_create", c)
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "rental.created",
            id=cid,
            give=registry.fmt_res_dict(give),
            repay=registry.fmt_res_dict(repay),
            time=registry.fmt_cd(duration),
        ),
        keypad=registry.market_keypad(),
    )


registry.handle_create_rental = handle_create_rental


def find_rental_contract(cid: int) -> dict[str, Any] | None:
    for c in registry.game.get("resource_rentals", []):
        if int(c.get("id", -1)) == int(cid) and c.get("status") == "open":
            return c
    return None


registry.find_rental_contract = find_rental_contract


def handle_accept_rental(chat_id: str, text: str) -> None:
    cid = registry.parse_order_id(text)
    c = registry.find_rental_contract(cid or -1)
    if not c:
        registry.send(
            chat_id, registry.T("rental.not_found"), keypad=registry.market_keypad()
        )
        return
    if c.get("lender") == chat_id:
        registry.send(
            chat_id,
            registry.T("rental.cannot_accept_own"),
            keypad=registry.market_keypad(),
        )
        return
    if registry.player_has_active_rental(chat_id):
        registry.send(
            chat_id, registry.T("rental.active_limit"), keypad=registry.market_keypad()
        )
        return
    borrower = registry.get_player(chat_id)
    lender = registry.get_player(c["lender"])
    for r, q in c.get("give", {}).items():
        registry.add_amount(borrower, r, int(q))
    c["borrower"] = chat_id
    c["accepted_at"] = registry.iso(registry.now())
    c["due_at"] = registry.iso(
        registry.now() + timedelta(seconds=int(c.get("duration_seconds", 0)))
    )
    c["remaining"] = dict(c.get("repay", {}))
    c["status"] = "accepted"
    borrower.setdefault("stats", {})["rentals_taken"] = (
        int(borrower.get("stats", {}).get("rentals_taken", 0)) + 1
    )
    lender.setdefault("stats", {})["rentals_given"] = (
        int(lender.get("stats", {}).get("rentals_given", 0)) + 1
    )
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "rental.accepted_borrower",
            got=registry.fmt_res_dict(c.get("give", {})),
            repay=registry.fmt_res_dict(c.get("repay", {})),
            due=registry.fmt_dt(c.get("due_at")),
            lender=registry.display_name(registry.player_name(c["lender"])),
        ),
        keypad=registry.market_keypad(),
    )
    registry.send(
        c["lender"],
        registry.T(
            "rental.accepted_lender",
            borrower=registry.display_name(registry.player_name(chat_id)),
            give=registry.fmt_res_dict(c.get("give", {})),
            repay=registry.fmt_res_dict(c.get("repay", {})),
            due=registry.fmt_dt(c.get("due_at")),
        ),
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_accept_rental = handle_accept_rental


def handle_my_rentals(chat_id: str) -> None:
    registry.process_resource_rentals()
    mine = [
        c
        for c in registry.game.get("resource_rentals", [])
        if c.get("lender") == chat_id or c.get("borrower") == chat_id
    ]
    active = [c for c in mine if c.get("status") in {"open", "accepted", "overdue"}]
    if not active:
        registry.send(
            chat_id, registry.T("rental.my_empty"), keypad=registry.rental_keypad()
        )
        return
    lines = []
    rows: list[list[str]] = []
    for c in active[:10]:
        role = "قرض\u200cدهنده" if c.get("lender") == chat_id else "قرض\u200cگیرنده"
        lines.append(
            registry.T(
                "rental.my_line",
                id=c["id"],
                role=role,
                status=c.get("status"),
                give=registry.fmt_res_dict(c.get("give", {})),
                repay=registry.fmt_res_dict(c.get("remaining") or c.get("repay", {})),
                due=registry.fmt_dt(c.get("due_at"))
                if c.get("due_at")
                else "هنوز قبول نشده",
            )
        )
        if c.get("status") == "open" and c.get("lender") == chat_id:
            rows.append([f"لغو قرارداد #{c['id']}"])
    rows.append([registry.B("back_market"), registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T("rental.my_list", contracts="\n\n".join(lines)),
        keypad=registry.make_keypad(rows),
    )


registry.handle_my_rentals = handle_my_rentals


def handle_cancel_rental(chat_id: str, text: str) -> None:
    cid = registry.parse_order_id(text)
    c = registry.find_rental_contract(cid or -1)
    if not c or c.get("lender") != chat_id:
        registry.send(
            chat_id, registry.T("rental.not_found"), keypad=registry.market_keypad()
        )
        return
    p = registry.get_player(chat_id)
    for r, q in c.get("give", {}).items():
        registry.add_amount(p, r, int(q))
    c["status"] = "cancelled"
    c["cancelled_at"] = registry.iso(registry.now())
    registry.save_game()
    registry.send(
        chat_id, registry.T("rental.cancelled", id=cid), keypad=registry.market_keypad()
    )


registry.handle_cancel_rental = handle_cancel_rental
