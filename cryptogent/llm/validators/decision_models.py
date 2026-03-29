from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationOutcome:
    decision: str  # accepted | accepted_with_warning | rejected | retry_needed
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
