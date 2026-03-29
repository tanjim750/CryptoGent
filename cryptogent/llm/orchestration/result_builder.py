from __future__ import annotations

from cryptogent.llm.contracts import LLMRawResponse, LLMTaskName, LLMTaskResult, ParsedLLMResult, ValidationDecision
from cryptogent.llm.validators.decision_models import ValidationOutcome


def build_validation_decision(outcome: ValidationOutcome | None) -> ValidationDecision | None:
    if outcome is None:
        return None
    is_valid = outcome.decision in ("accepted", "accepted_with_warning")
    reason = outcome.decision
    return ValidationDecision(
        is_valid=is_valid,
        reason=reason,
        errors=tuple(outcome.errors),
        confidence=None,
    )


def build_task_result(
    *,
    task_name: LLMTaskName,
    raw_response: LLMRawResponse,
    parsed: ParsedLLMResult | None,
    outcome: ValidationOutcome | None,
    final_output: dict | None,
) -> LLMTaskResult:
    status = "error"
    if outcome is None:
        status = "error"
    elif outcome.decision in ("accepted", "accepted_with_warning"):
        status = "success"
    elif outcome.decision == "retry_needed":
        status = "retry_needed"
    elif outcome.decision == "rejected":
        status = "rejected"

    return LLMTaskResult(
        task_name=task_name,
        status=status,
        raw_response=raw_response,
        parsed=parsed,
        validation=build_validation_decision(outcome),
        final_output=final_output,
    )
