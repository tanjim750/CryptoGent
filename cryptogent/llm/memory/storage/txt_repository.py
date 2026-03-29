from __future__ import annotations

from pathlib import Path
from typing import Iterable

from cryptogent.llm.memory.storage.memory_item import MemoryItem
from cryptogent.llm.memory.storage.repository import MemoryRepository


class TxtMemoryRepository(MemoryRepository):
    def __init__(self, path: Path) -> None:
        self._path = path.expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, item: MemoryItem) -> None:
        if not item.content:
            return
        line = f"{item.timestamp_utc} {item.memory_key} {item.role}: {item.content}\n"
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)

    def fetch_recent(self, *, memory_key: str, limit: int | None, since_utc: str | None = None) -> Iterable[MemoryItem]:
        items = self._load_all(memory_key=memory_key, since_utc=since_utc)
        if limit is None:
            return items
        return items[-limit:]

    def fetch_by_task(
        self, *, memory_key: str, task_name: str, limit: int | None, since_utc: str | None = None
    ) -> Iterable[MemoryItem]:
        items = [
            item
            for item in self._load_all(memory_key=memory_key, since_utc=since_utc)
            if item.task_name == task_name
        ]
        if limit is None:
            return items
        return items[-limit:]

    def _load_all(self, *, memory_key: str, since_utc: str | None) -> list[MemoryItem]:
        if not self._path.exists():
            return []
        out: list[MemoryItem] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" ", 2)
                if len(parts) < 3:
                    continue
                ts, key, rest = parts[0], parts[1], parts[2]
                if key != memory_key:
                    continue
                if since_utc and ts < since_utc:
                    continue
                if ":" not in rest:
                    continue
                role, content = rest.split(":", 1)
                out.append(
                    MemoryItem(
                        memory_key=key,
                        task_name="unknown",
                        role=role.strip(),
                        content=content.strip(),
                        timestamp_utc=ts,
                        source="txt",
                        metadata=None,
                    )
                )
        return out
