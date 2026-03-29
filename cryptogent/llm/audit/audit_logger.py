from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptogent.llm.audit.models import AuditRecord
from cryptogent.llm.audit.repositories import JsonlAuditRepository


@dataclass(frozen=True)
class AuditOptions:
    include_prompt_text: bool = False


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        redacted: dict[str, Any] = {}
        for k, v in obj.items():
            key = str(k).lower()
            if any(token in key for token in ("api_key", "api_secret", "secret", "token", "credential")):
                redacted[k] = "***REDACTED***"
            elif key == "memory_items" or key == "memory":
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = _redact(v)
        return redacted
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


def build_audit_record(
    *,
    event: dict[str, Any],
    retry_count: int,
    error_summary: str | None,
    context_size: int,
    memory_size: int,
    options: AuditOptions,
) -> AuditRecord:
    created_at = datetime.now(tz=timezone.utc).isoformat()
    event = _redact(event)
    return AuditRecord(
        task_name=str(event.get("task_name") or ""),
        prompt_version=event.get("prompt_version"),
        schema_version=event.get("schema_version"),
        provider=str(event.get("provider") or ""),
        model=str(event.get("model") or ""),
        latency_ms=event.get("latency_ms"),
        usage=event.get("usage") if isinstance(event.get("usage"), dict) else None,
        validation_decision=event.get("validation_decision"),
        retry_count=retry_count,
        error_summary=error_summary,
        context_size=context_size,
        memory_size=memory_size,
        created_at_utc=created_at,
        system_message=event.get("system_message") if options.include_prompt_text else None,
        user_message=event.get("user_message") if options.include_prompt_text else None,
    )


def write_audit_trace(
    *,
    repository: JsonlAuditRepository,
    record: AuditRecord,
) -> None:
    repository.append(record)
