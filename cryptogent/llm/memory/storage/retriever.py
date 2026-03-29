from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from cryptogent.llm.memory.policies import MemoryPolicy
from cryptogent.llm.memory.storage.memory_item import MemoryItem
from cryptogent.llm.memory.storage.repository import MemoryRepository


class MemoryRetriever:
    def __init__(self, repo: MemoryRepository) -> None:
        self._repo = repo

    def retrieve(
        self, *, memory_key: str, task_name: str, policy: MemoryPolicy
    ) -> Iterable[MemoryItem]:
        since_utc = None
        if policy.recency_days is not None:
            since_utc = (datetime.now(tz=timezone.utc) - timedelta(days=policy.recency_days)).isoformat()
        return self._repo.fetch_recent(memory_key=memory_key, limit=policy.max_items, since_utc=since_utc)
