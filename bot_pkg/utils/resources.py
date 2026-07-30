from typing import Any

from bot_pkg.registry import registry


def res_key(value: str) -> str | None:
    return registry.RES_ALIASES.get(
        (value or "").strip().lower()
    ) or registry.RES_ALIASES.get((value or "").strip())


def amount_of(p: dict[str, Any], key: str) -> int:
    if key == "water":
        return int(p.get("water", 0))

    return int(p.get("resources", {}).get(key, 0))


def add_amount(
    p: dict[str, Any],
    key: str,
    amount: int,
) -> None:
    if key == "water":
        p["water"] = int(p.get("water", 0)) + int(amount)
    else:
        p.setdefault("resources", {})[key] = int(
            p.get("resources", {}).get(key, 0)
        ) + int(amount)


def pay_cost(
    p: dict[str, Any],
    cost: dict[str, int],
) -> None:
    for key, amount in cost.items():
        add_amount(p, key, -int(amount))


def fmt_res_amount(
    key: str,
    amount: int,
    sign: str = "×",
) -> str:
    icon = registry.RES_ICON.get(key, "")
    name = registry.RES_NAME.get(key, key)

    return f"{icon} {name} {sign} {amount}"


def fmt_res_dict(
    cost: dict[str, int],
) -> str:
    if not cost:
        return "—"

    return " + ".join(fmt_res_amount(k, v) for k, v in cost.items())


def fmt_res_lines(
    cost: dict[str, int],
) -> str:
    if not cost:
        return "—"

    return "\n".join(f"• {fmt_res_amount(k, v)}" for k, v in cost.items())


def fmt_res_loss(
    cost: dict[str, int],
) -> str:
    if not cost:
        return "• بدون ضرر منابع"

    return "\n".join(
        f"• {registry.RES_ICON.get(k, '')} {registry.RES_NAME.get(k, k)}: -{v}"
        for k, v in cost.items()
    )


def fmt_res_shortage(
    cost: dict[str, int],
    p: dict[str, Any],
) -> str:
    lines = ["📦 نیاز / موجودی / کمبود"]

    for r, need in cost.items():
        have = amount_of(p, r)
        miss = max(0, int(need) - have)

        status = "✅ کافی" if miss == 0 else f"❌ کمبود: {miss}"

        lines.append(
            f"• {registry.RES_ICON.get(r, '')} "
            f"{registry.RES_NAME.get(r, r)}: "
            f"نیاز {need} | داری {have} | {status}"
        )

    return "\n".join(lines)


def has_resources(
    p: dict[str, Any],
    cost: dict[str, int],
) -> bool:
    return all(amount_of(p, r) >= int(q) for r, q in cost.items())
