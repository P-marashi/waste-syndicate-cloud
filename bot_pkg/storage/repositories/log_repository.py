from typing import Any


class LogRepository:
    """Append-only log collection (`news_feed`, `group_radio_log`,
    `system_stock_log`). These never had a stable id in the old schema —
    just append to a list and slice off the front. Each entry now gets a
    real document with a monotonic `seq` for ordering, instead of living
    forever inside the `meta` document's arrays.
    """

    def __init__(self, db, collection_name: str):
        self._db = db
        self._collection_name = collection_name

    @property
    def collection(self):
        return self._db[self._collection_name]

    def ensure_indexes(self) -> None:
        self.collection.create_index("seq")

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        cursor = self.collection.find().sort("seq", 1)
        docs = [self._strip(doc) for doc in cursor]
        if limit is not None and len(docs) > limit:
            docs = docs[-limit:]
        return docs

    def append(self, entry: dict[str, Any]) -> None:
        next_seq = self.collection.count_documents({})
        self.collection.insert_one({**entry, "seq": next_seq})

    def replace_all(self, items: list[dict[str, Any]]) -> None:
        self.collection.delete_many({})
        if not items:
            return
        docs = [{**item, "seq": i} for i, item in enumerate(items)]
        self.collection.insert_many(docs)

    @staticmethod
    def _strip(doc: dict[str, Any]) -> dict[str, Any]:
        doc = dict(doc)
        doc.pop("_id", None)
        doc.pop("seq", None)
        return doc
