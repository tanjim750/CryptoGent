from __future__ import annotations

from pathlib import Path

from cryptogent.llm.memory.storage.repository import MemoryRepository
from cryptogent.llm.memory.storage.sqlite_repository import SqliteMemoryRepository
from cryptogent.llm.memory.storage.jsonl_repository import JsonlMemoryRepository
from cryptogent.llm.memory.storage.in_memory_repository import InMemoryRepository
from cryptogent.llm.memory.storage.txt_repository import TxtMemoryRepository


_IN_MEMORY_SINGLETON: InMemoryRepository | None = None


def build_repository(*, backend: str, path: Path) -> MemoryRepository:
    name = backend.strip().lower()
    if name == "sqlite":
        return SqliteMemoryRepository(path=path)
    if name == "jsonl":
        return JsonlMemoryRepository(path=path)
    if name == "memory":
        global _IN_MEMORY_SINGLETON
        if _IN_MEMORY_SINGLETON is None:
            _IN_MEMORY_SINGLETON = InMemoryRepository()
        return _IN_MEMORY_SINGLETON
    if name == "txt":
        return TxtMemoryRepository(path=path)
    raise ValueError(f"Unsupported memory backend: {backend}")
