from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    task_name: str
    prompt_version: str | None
    schema_version: str | None
    provider: str
    model: str
    latency_ms: int | None
    usage: dict[str, Any] | None
    validation_decision: str | None
    retry_count: int
    error_summary: str | None
    context_size: int
    memory_size: int
    created_at_utc: str
    system_message: str | None = None
    user_message: str | None = None
