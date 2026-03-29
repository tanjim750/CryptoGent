from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2


def should_retry(*, reason: str, policy: RetryPolicy, attempt: int) -> bool:
    if attempt >= policy.max_attempts:
        return False
    return reason in ("retry_needed", "provider_error", "parse_error")
