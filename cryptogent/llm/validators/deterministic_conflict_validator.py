from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeterministicContext:
    allowed_symbols: set[str] | None = None
    budget_limit: float | None = None
    risk_cap: float | None = None
    safety_violations: tuple[str, ...] = ()
    invalid_actions: tuple[str, ...] = ()


def validate_deterministic_conflicts(
    data: dict[str, Any], ctx: DeterministicContext | None
) -> tuple[list[str], list[str]]:
    if ctx is None:
        return [], []
    errors: list[str] = []
    warnings: list[str] = []

    symbol = data.get("symbol")
    if symbol and ctx.allowed_symbols is not None:
        if str(symbol).upper() not in ctx.allowed_symbols:
            errors.append("symbol_not_allowed")

    for key in ("budget", "budget_amount"):
        if key in data and ctx.budget_limit is not None:
            try:
                if float(data.get(key)) > ctx.budget_limit:
                    errors.append("budget_limit_exceeded")
            except Exception:
                errors.append("budget_invalid")

    for key in ("risk", "risk_amount"):
        if key in data and ctx.risk_cap is not None:
            try:
                if float(data.get(key)) > ctx.risk_cap:
                    errors.append("risk_cap_exceeded")
            except Exception:
                errors.append("risk_invalid")

    if ctx.safety_violations:
        errors.extend([f"safety_violation:{v}" for v in ctx.safety_violations])
    if ctx.invalid_actions:
        errors.extend([f"invalid_action:{v}" for v in ctx.invalid_actions])

    return errors, warnings
