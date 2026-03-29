from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cryptogent.llm.contracts import LLMTaskName, ParsedLLMResult, SchemaBundle
from cryptogent.llm.validators.decision_models import ValidationOutcome
from cryptogent.llm.validators.deterministic_conflict_validator import DeterministicContext, validate_deterministic_conflicts
from cryptogent.llm.validators.policy_validator import validate_policy
from cryptogent.llm.validators.schema_validator import validate_schema


@dataclass(frozen=True)
class ValidationContext:
    task_name: LLMTaskName
    schema_bundle: SchemaBundle | None
    deterministic_context: DeterministicContext | None = None


def validate_result(parsed: ParsedLLMResult, ctx: ValidationContext) -> ValidationOutcome:
    if parsed.structured is None:
        return ValidationOutcome(decision="retry_needed", errors=parsed.warnings)

    data: dict[str, Any] = parsed.structured

    errors: list[str] = []
    warnings: list[str] = list(parsed.warnings)

    schema_errors, schema_warnings = validate_schema(data, ctx.schema_bundle)
    errors.extend(schema_errors)
    warnings.extend(schema_warnings)

    policy_errors, policy_warnings = validate_policy(ctx.task_name, data)
    errors.extend(policy_errors)
    warnings.extend(policy_warnings)

    det_errors, det_warnings = validate_deterministic_conflicts(data, ctx.deterministic_context)
    errors.extend(det_errors)
    warnings.extend(det_warnings)

    if errors:
        if any(err.startswith("missing_required_fields") for err in errors):
            return ValidationOutcome(decision="retry_needed", warnings=tuple(warnings), errors=tuple(errors))
        return ValidationOutcome(decision="rejected", warnings=tuple(warnings), errors=tuple(errors))

    if warnings:
        return ValidationOutcome(decision="accepted_with_warning", warnings=tuple(warnings), errors=tuple(errors))
    return ValidationOutcome(decision="accepted", warnings=tuple(warnings), errors=tuple(errors))
