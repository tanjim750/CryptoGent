from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from cryptogent.llm.memory.storage.memory_item import MemoryItem


class MemoryRepository(ABC):
    @abstractmethod
    def append(self, item: MemoryItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_recent(
        self, *, memory_key: str, limit: int | None, since_utc: str | None = None
    ) -> Iterable[MemoryItem]:
        raise NotImplementedError

    @abstractmethod
    def fetch_by_task(
        self, *, memory_key: str, task_name: str, limit: int | None, since_utc: str | None = None
    ) -> Iterable[MemoryItem]:
        raise NotImplementedError
