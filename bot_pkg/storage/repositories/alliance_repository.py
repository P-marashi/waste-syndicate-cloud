from typing import Any


class AllianceRepository:
    """Targeted CRUD for the `alliances` collection, keyed by alliance name."""

    def __init__(self, db):
        self._db = db

    @property
    def collection(self):
        return self._db["alliances"]

    def get(self, name: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"_id": str(name)})
        if doc is None:
            return None
        doc = dict(doc)
        doc.pop("_id", None)
        return doc

    def save(self, name: str, alliance: dict[str, Any]) -> None:
        self.collection.update_one(
            {"_id": str(name)},
            {"$set": {**alliance, "_id": str(name)}},
            upsert=True,
        )

    def delete(self, name: str) -> None:
        self.collection.delete_one({"_id": str(name)})

    def list_all(self) -> dict[str, dict[str, Any]]:
        return {str(doc.pop("_id")): doc for doc in self.collection.find()}

    def ensure_indexes(self) -> None:
        self.collection.create_index("owner")
