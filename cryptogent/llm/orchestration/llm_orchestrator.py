from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cryptogent.llm.contracts import LLMRawResponse, LLMTaskName, LLMTaskResult, ParsedLLMResult, SchemaBundle
from cryptogent.llm.orchestration.result_builder import build_task_result
from cryptogent.llm.orchestration.retry_manager import RetryPolicy, should_retry
from cryptogent.llm.orchestration.task_runner import AuditHook, run_once
from cryptogent.llm.providers.base import BaseProvider
from cryptogent.llm.validators import DeterministicContext


@dataclass(frozen=True)
class OrchestrationOptions:
    max_attempts: int = 2
    strict_required: bool = True
    enable_memory: bool = True
    prompt_version: str | None = None
    token_estimator: str | None = None
    max_context_tokens: int | None = None
    enforce_task_budget: str | None = None
    enforce_provider_cap: str | None = None


def run_llm_task(
    *,
    task_name: LLMTaskName,
    raw_inputs: dict[str, Any],
    provider: BaseProvider | None = None,
    schema_bundle: SchemaBundle | None = None,
    deterministic_context: DeterministicContext | None = None,
    options: OrchestrationOptions | None = None,
    audit_hook: AuditHook | None = None,
) -> LLMTaskResult:
    if provider is None:
        raise ValueError("Provider is required (no default provider configured yet).")
    options = options or OrchestrationOptions()
    policy = RetryPolicy(max_attempts=options.max_attempts)

    last_raw: LLMRawResponse | None = None
    last_parsed: ParsedLLMResult | None = None
    last_outcome = None
    final_output = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            raw, _ctx, _mem, _prompt, parsed, outcome, final_output = run_once(
                task_name=task_name,
                raw_inputs=raw_inputs,
                provider=provider,
                schema_bundle=schema_bundle,
                deterministic_context=deterministic_context,
                enable_memory=options.enable_memory,
                strict_required=options.strict_required,
                prompt_version=options.prompt_version,
                token_estimator=options.token_estimator,
                max_context_tokens=options.max_context_tokens,
                enforce_task_budget=options.enforce_task_budget,
                enforce_provider_cap=options.enforce_provider_cap,
                audit_hook=audit_hook,
            )
            last_raw = raw
            last_parsed = parsed
            last_outcome = outcome

            if outcome.decision in ("accepted", "accepted_with_warning"):
                return build_task_result(
                    task_name=task_name,
                    raw_response=raw,
                    parsed=parsed,
                    outcome=outcome,
                    final_output=final_output,
                )
            if outcome.decision == "retry_needed":
                if should_retry(reason="retry_needed", policy=policy, attempt=attempt):
                    continue
            return build_task_result(
                task_name=task_name,
                raw_response=raw,
                parsed=parsed,
                outcome=outcome,
                final_output=final_output,
            )
        except Exception as exc:
            if should_retry(reason="provider_error", policy=policy, attempt=attempt):
                continue
            break

    if last_raw is None:
        last_raw = LLMRawResponse(
            provider_name="unknown",
            model="unknown",
            content="",
            raw_payload={"error": "provider_failed"},
            usage=None,
            latency_ms=None,
            finish_reason=None,
            created_at_utc="",
        )
    return build_task_result(
        task_name=task_name,
        raw_response=last_raw,
        parsed=last_parsed,
        outcome=last_outcome,
        final_output=final_output,
    )
