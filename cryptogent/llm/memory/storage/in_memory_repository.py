from __future__ import annotations

from typing import Iterable

from cryptogent.llm.memory.storage.memory_item import MemoryItem
from cryptogent.llm.memory.storage.repository import MemoryRepository


class InMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    def append(self, item: MemoryItem) -> None:
        if not item.content:
            return
        self._items.append(item)

    def fetch_recent(self, *, memory_key: str, limit: int | None, since_utc: str | None = None) -> Iterable[MemoryItem]:
        items = [i for i in self._items if i.memory_key == memory_key]
        if since_utc:
            items = [i for i in items if i.timestamp_utc >= since_utc]
        if limit is None:
            return items
        return items[-limit:]

    def fetch_by_task(
        self, *, memory_key: str, task_name: str, limit: int | None, since_utc: str | None = None
    ) -> Iterable[MemoryItem]:
        items = [i for i in self._items if i.memory_key == memory_key and i.task_name == task_name]
        if since_utc:
            items = [i for i in items if i.timestamp_utc >= since_utc]
        if limit is None:
            return items
        return items[-limit:]
