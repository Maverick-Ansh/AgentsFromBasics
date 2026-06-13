"""A tiny persistent store.

The mock Calendar / Tasks / Booking / Email services and long-term memory all
need somewhere durable to keep data. Instead of a database we use one JSON file
per "collection" — trivial to read and inspect while you're learning. Swap this
for SQLite or Postgres later and nothing above it has to change.
"""
import json
import os
import threading

from . import config


class Collection:
    """A list of dict records persisted to a JSON file, with auto-increment IDs."""

    def __init__(self, name: str):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        self.path = os.path.join(config.DATA_DIR, f"{name}.json")
        self._lock = threading.Lock()  # the Telegram bot is multi-threaded
        self._items: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._items, f, indent=2)

    def add(self, record: dict) -> dict:
        with self._lock:
            next_id = max((i["id"] for i in self._items), default=0) + 1
            record = {"id": next_id, **record}
            self._items.append(record)
            self._save()
            return record

    def all(self) -> list[dict]:
        return list(self._items)

    def find(self, item_id: int) -> dict | None:
        return next((i for i in self._items if i["id"] == item_id), None)

    def update(self, item_id: int, **changes) -> dict | None:
        with self._lock:
            item = self.find(item_id)
            if item is None:
                return None
            item.update(changes)
            self._save()
            return item

    def delete(self, item_id: int) -> bool:
        with self._lock:
            before = len(self._items)
            self._items = [i for i in self._items if i["id"] != item_id]
            self._save()
            return len(self._items) < before
