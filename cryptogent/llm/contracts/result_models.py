from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .provider_models import LLMRawResponse
from .task_models import LLMTaskName


@dataclass(frozen=True)
class ParsedLLMResult:
    task_name: LLMTaskName
    content: str
    structured: dict[str, Any] | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationDecision:
    is_valid: bool
    reason: str | None
    errors: tuple[str, ...] = ()
    confidence: float | None = None


@dataclass(frozen=True)
class LLMTaskResult:
    task_name: LLMTaskName
    status: str
    raw_response: LLMRawResponse
    parsed: ParsedLLMResult | None
    validation: ValidationDecision | None
    final_output: dict[str, Any] | None
