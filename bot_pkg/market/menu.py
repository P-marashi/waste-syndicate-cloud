from ..registry import registry


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
