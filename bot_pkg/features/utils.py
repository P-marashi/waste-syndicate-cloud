from ..registry import registry


def registered_player_ids(include_banned: bool = False) -> list[str]:
    return [
        cid
        for cid, p in registry.game.get("players", {}).items()
        if p.get("registered") and (include_banned or not p.get("banned"))
    ]


registry.registered_player_ids = registered_player_ids
