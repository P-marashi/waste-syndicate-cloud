from typing import Any


class PlayerRepository:
    """Targeted CRUD for the `players` collection.

    One document per player, keyed by chat_id. This already worked
    reasonably before (players were never part of the `meta` blob) — this
    class mainly gives it a name and a place to grow real queries
    (`find_banned`, `top_by_level`, ...) instead of loading every player
    into memory and filtering in Python.
    """

    def __init__(self, db):
        self._db = db

    @property
    def collection(self):
        return self._db["players"]

    def get(self, chat_id: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"_id": str(chat_id)})
        if doc is None:
            return None
        doc = dict(doc)
        doc.pop("_id", None)
        return doc

    def save(self, chat_id: str, player: dict[str, Any]) -> None:
        self.collection.update_one(
            {"_id": str(chat_id)},
            {"$set": {**player, "_id": str(chat_id)}},
            upsert=True,
        )

    def delete(self, chat_id: str) -> None:
        self.collection.delete_one({"_id": str(chat_id)})

    def list_all(self) -> dict[str, dict[str, Any]]:
        """Full table load — kept for the transitional `load_game()` bridge.

        Once handlers read/write single players through `get`/`save`
        instead of mutating `registry.game["players"]`, this stops being
        called on every request.
        """
        return {str(doc.pop("_id")): doc for doc in self.collection.find()}

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"name": name})
        if doc is None:
            return None
        doc = dict(doc)
        doc["chat_id"] = doc.pop("_id")
        return doc

    def find_banned(self) -> list[dict[str, Any]]:
        return [
            {**{k: v for k, v in doc.items() if k != "_id"}, "chat_id": doc["_id"]}
            for doc in self.collection.find({"banned": True})
        ]

    def count(self) -> int:
        return self.collection.count_documents({})

    def ensure_indexes(self) -> None:
        self.collection.create_index("name")
        self.collection.create_index("banned")
        self.collection.create_index("alliance")
