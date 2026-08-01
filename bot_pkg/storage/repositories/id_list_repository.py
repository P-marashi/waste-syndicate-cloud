from typing import Any


class IdListRepository:
    """Repository for collections that used to be a Python list embedded in
    the giant `meta` document (`market_orders`, `barter_orders`,
    `resource_rentals`, `private_messages`, `admin_logs`).

    Each item becomes its own Mongo document (keyed by its existing
    integer `id` field) instead of an element of an ever-growing array on
    one shared document. This is what actually fixes the "whole game gets
    rewritten on every action" problem and avoids ever hitting the 16MB
    document size limit as the game grows.

    `replace_all` is a *transitional* bridge: it lets `save_game()` keep
    working exactly as before (dump the in-memory list, sync it to Mongo)
    while the rest of the code still mutates `registry.game[key]` as a
    plain list. Once a handler is rewritten to call `add`/`update`/`delete`
    directly (Phase 2), `replace_all` is no longer needed for that data.
    """

    def __init__(self, db, collection_name: str, indexes: tuple[str, ...] = ()):
        self._db = db
        self._collection_name = collection_name
        self._indexes = indexes

    @property
    def collection(self):
        return self._db[self._collection_name]

    def ensure_indexes(self) -> None:
        for field in self._indexes:
            self.collection.create_index(field)

    def list_all(self) -> list[dict[str, Any]]:
        return [self._strip(doc) for doc in self.collection.find()]

    def get(self, item_id: int) -> dict[str, Any] | None:
        doc = self.collection.find_one({"_id": item_id})
        return self._strip(doc) if doc else None

    def add(self, item: dict[str, Any]) -> None:
        if "id" not in item:
            raise ValueError("item must have an 'id' field")
        self.collection.insert_one({**item, "_id": item["id"]})

    def update(self, item_id: int, fields: dict[str, Any]) -> None:
        self.collection.update_one({"_id": item_id}, {"$set": fields})

    def delete(self, item_id: int) -> None:
        self.collection.delete_one({"_id": item_id})

    def replace_all(self, items: list[dict[str, Any]]) -> None:
        ids = [item["id"] for item in items if "id" in item]

        if ids:
            self.collection.delete_many({"_id": {"$nin": ids}})
        else:
            self.collection.delete_many({})

        for item in items:
            if "id" not in item:
                continue
            self.collection.update_one(
                {"_id": item["id"]},
                {"$set": {**item, "_id": item["id"]}},
                upsert=True,
            )

    @staticmethod
    def _strip(doc: dict[str, Any]) -> dict[str, Any]:
        doc = dict(doc)
        doc["id"] = doc.pop("_id")
        return doc
