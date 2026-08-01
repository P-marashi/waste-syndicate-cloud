"""Single place that knows the full list of Mongo collections and how to
build a repository for each one. `persistence.py`, the migration script,
and any future service code should get repositories from here instead of
touching `db["some_collection"]` directly.
"""

from .database import get_db
from .repositories.alliance_repository import AllianceRepository
from .repositories.id_list_repository import IdListRepository
from .repositories.log_repository import LogRepository
from .repositories.meta_repository import MetaRepository
from .repositories.player_repository import PlayerRepository

# id-keyed collections that replace the old `meta.<key>` arrays
ID_LIST_KEYS = (
    "market_orders",
    "barter_orders",
    "resource_rentals",
    "private_messages",
    "admin_logs",
)

# append-only log collections that replace the old `meta.<key>` arrays
LOG_KEYS = (
    "news_feed",
    "group_radio_log",
    "system_stock_log",
)

_INDEXES: dict[str, tuple[str, ...]] = {
    "market_orders": ("seller_id", "status", "resource"),
    "barter_orders": ("seller_id", "status"),
    "resource_rentals": ("owner_id", "renter_id"),
    "private_messages": ("to_id", "from_id"),
    "admin_logs": ("admin_id",),
}

_repos_cache: dict[int, dict] = {}


def build_repositories(db=None, ensure_indexes: bool = False) -> dict:
    """Return (and cache) the full set of repositories for a given db
    handle. Passing a fresh `db` (e.g. a mongomock database in tests)
    gets its own independent set of repository instances.
    """
    db = db if db is not None else get_db()
    key = id(db)

    if key not in _repos_cache:
        repos: dict = {
            "players": PlayerRepository(db),
            "alliances": AllianceRepository(db),
            "meta": MetaRepository(db),
        }

        for name in ID_LIST_KEYS:
            repos[name] = IdListRepository(db, name, indexes=_INDEXES.get(name, ()))

        for name in LOG_KEYS:
            repos[name] = LogRepository(db, name)

        _repos_cache[key] = repos

    repos = _repos_cache[key]

    if ensure_indexes:
        for repo in repos.values():
            if hasattr(repo, "ensure_indexes"):
                repo.ensure_indexes()

    return repos
