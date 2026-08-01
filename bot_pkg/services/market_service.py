"""Pure market math.

Extracted from `s11_market_core.py`. Covers: system reference pricing
(the buy/sell curve), resource-pair / barter / rental text parsing, the
rental profit-limit rule, and the daily system restock calculation.

NOT covered by this pass: order/barter/rental *creation*, *accept*, and
*cancel* flows. Those mutate shared game state (`chat_states`,
`market_orders`, multi-player `send()` calls) and are a bigger, riskier
extraction — left for a follow-up. This slice targets the parts that are
easy to get subtly wrong (price clamping at the edges, parsing malformed
input, the 1.3x profit-limit math) and were previously only reachable by
clicking through the live bot.
"""

from __future__ import annotations

import re
from typing import Callable


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


# ---------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------


def system_reference_price(
    base_price: int,
    supply: int,
    *,
    all_prices_mod: float = 1.0,
    resource_price_mod: float = 1.0,
) -> int:
    """The system's reference price for a resource: starts slightly
    above `base_price`, drops as `supply` grows (more supply = cheaper),
    clamped to [0.65x, 1.8x] of base, then scaled by any active world
    event price modifiers.
    """
    supply = max(0, int(supply))
    price = int(base_price * 1.05 - min(base_price * 0.35, supply * 0.25))
    price = max(int(base_price * 0.65), min(price, int(base_price * 1.8)))
    price = int(price * all_prices_mod)
    price = int(price * resource_price_mod)
    return max(1, price)


def system_buy_price(reference_price: int) -> int:
    """What the system pays a player selling to it (a quarter of the
    reference price — selling to the system is always a bad deal
    compared to the player market, by design).
    """
    return max(1, int(reference_price * 0.25))


def system_sell_price(reference_price: int) -> int:
    """What a player pays to buy from the system (2.5x reference —
    the system is a last resort, not a good source of supply).
    """
    return max(1, int(reference_price * 2.5))


# ---------------------------------------------------------------------
# Text parsing (order/barter/rental composition, e.g. "5 scrap = 3 glass")
# ---------------------------------------------------------------------


def parse_resource_pairs(
    text: str,
    resolve_resource: Callable[[str], str | None],
    valid_resources: set[str],
) -> dict[str, int] | None:
    """Parses alternating "<resource> <qty>" tokens, e.g. "آهن 5 پلاستیک 3".
    `resolve_resource` maps a localized token to a canonical resource key
    (this stays injected because the alias table is locale/text data,
    not game logic). Returns None on any malformed input — this function
    is deliberately strict, matching the original behavior.
    """
    if not text:
        return None

    tokens = re.findall(r"[\wآ-یئ]+|\d+", text.replace("×", " ").replace("،", " "))
    result: dict[str, int] = {}
    i = 0

    while i < len(tokens):
        resource = resolve_resource(tokens[i])
        if not resource or resource == "water" or resource not in valid_resources:
            return None
        if i + 1 >= len(tokens):
            return None
        qty = _safe_int(tokens[i + 1], -1)
        if qty <= 0:
            return None
        result[resource] = result.get(resource, 0) + qty
        i += 2

    return result or None


def parse_barter_text(
    text: str,
    resolve_resource: Callable[[str], str | None],
    valid_resources: set[str],
) -> tuple[dict[str, int], dict[str, int]] | None:
    """Parses "<give> = <want>" barter offers."""
    if "=" not in text:
        return None

    left, right = text.split("=", 1)
    give = parse_resource_pairs(left, resolve_resource, valid_resources)
    want = parse_resource_pairs(right, resolve_resource, valid_resources)

    if not give or not want:
        return None

    return give, want


def parse_rental_text(
    text: str,
    resolve_resource: Callable[[str], str | None],
    valid_resources: set[str],
) -> tuple[dict[str, int], dict[str, int], int] | None:
    """Parses "<give> = <repay> [hours]" rental offers. Duration defaults
    to 6 hours, clamped to [1, 48]. Returns (give, repay, duration_seconds).
    """
    if "=" not in text:
        return None

    left, right = text.split("=", 1)
    right_tokens = right.split()
    hours = 6

    if right_tokens and _safe_int(right_tokens[-1], -1) > 0:
        hours = _safe_int(right_tokens[-1], 6)
        right = " ".join(right_tokens[:-1])

    give = parse_resource_pairs(left, resolve_resource, valid_resources)
    repay = parse_resource_pairs(right, resolve_resource, valid_resources)

    if not give or not repay:
        return None

    hours = max(1, min(48, int(hours)))
    return give, repay, hours * 3600


# ---------------------------------------------------------------------
# Business rules
# ---------------------------------------------------------------------


def rental_profit_ok(give: dict[str, int], repay: dict[str, int]) -> bool:
    """Blocks single-resource rentals demanding more than 1.3x back —
    stops rentals from being used as a disguised high-interest loan
    shark scheme. Multi-resource rentals aren't checked (out of scope
    for the original rule too).
    """
    if len(give) == 1 and len(repay) == 1:
        give_resource, give_qty = next(iter(give.items()))
        repay_resource, repay_qty = next(iter(repay.items()))
        if give_resource == repay_resource and int(repay_qty) > int(
            give_qty * 1.3 + 0.999
        ):
            return False
    return True


# ---------------------------------------------------------------------
# Daily system restock
# ---------------------------------------------------------------------


def compute_daily_restock(
    current_supply: dict[str, int],
    resources: list[str],
    daily_amounts: dict[str, int],
    caps: dict[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    """Computes the next `market_supply` state and what got added today,
    respecting each resource's daily cap. Doesn't touch `registry.game`
    or check "did today's restock already happen" — that's still the
    handler's job (it needs `today_key()`/`now()`, which are I/O-ish
    system clock reads, not game math).
    """
    new_supply = dict(current_supply)
    added: dict[str, int] = {}

    for resource in resources:
        current = max(0, int(new_supply.get(resource, 0)))
        daily = max(0, int(daily_amounts.get(resource, 0)))
        cap = max(daily, int(caps.get(resource, daily)))
        qty = max(0, min(daily, cap - current))

        if qty > 0:
            new_supply[resource] = current + qty
            added[resource] = qty
        else:
            new_supply[resource] = current

    return new_supply, added
