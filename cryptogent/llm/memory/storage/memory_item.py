from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    memory_key: str
    task_name: str
    role: str
    content: str
    timestamp_utc: str
    source: str | None = None
    score: float | None = None
    metadata: dict[str, Any] | None = None
