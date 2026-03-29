from __future__ import annotations

import json
from typing import Any, Callable

from cryptogent.llm.contracts import (
    LLMContextBundle,
    LLMRawResponse,
    LLMTaskName,
    MemoryBundle,
    ParsedLLMResult,
    PromptPackage,
    ProviderRequest,
    SchemaBundle,
)
from cryptogent.llm.context import ContextManager
from cryptogent.llm.memory import MemoryManager
from cryptogent.llm.parsers import parse_response
from cryptogent.llm.prompts import build_guardrails, format_schema, get_prompt_template
from cryptogent.llm.prompts.assembler import assemble_messages
from cryptogent.llm.token_policy import allocate_budget, apply_truncation
from cryptogent.llm.token_policy.token_estimator import estimate_tokens, estimate_tokens_with
from cryptogent.llm.validators import DeterministicContext, ValidationContext, validate_result
from cryptogent.llm.providers.base import BaseProvider
from cryptogent.llm.validators.decision_models import ValidationOutcome


AuditHook = Callable[[dict[str, Any]], None]


def run_once(
    *,
    task_name: LLMTaskName,
    raw_inputs: dict[str, Any],
    provider: BaseProvider,
    schema_bundle: SchemaBundle | None,
    deterministic_context: DeterministicContext | None,
    enable_memory: bool,
    strict_required: bool,
    prompt_version: str | None,
    token_estimator: str | None,
    max_context_tokens: int | None,
    enforce_task_budget: str | None,
    enforce_provider_cap: str | None,
    audit_hook: AuditHook | None,
) -> tuple[
    LLMRawResponse,
    LLMContextBundle,
    MemoryBundle | None,
    PromptPackage,
    ParsedLLMResult,
    ValidationOutcome,
    dict | None,
]:
    context_manager = ContextManager()
    memory_manager = MemoryManager()

    context_bundle = context_manager.build(
        task_name=task_name,
        raw_inputs=raw_inputs,
        constraints=None,
        options=None,
        memory=None,
    )

    memory_bundle = None
    if enable_memory:
        memory_bundle = memory_manager.retrieve_memory(
            task_name=task_name,
            memory_key=str(raw_inputs.get("memory_key") or "") or None,
            raw_inputs=raw_inputs,
            conversation_state=raw_inputs.get("conversation_state"),
            retrieval_limit=None,
            policy=None,
        )

    def _mode(value: str | None) -> str:
        if not value:
            return "off"
        return value.strip().lower()

    enforce_task = _mode(enforce_task_budget)
    enforce_provider = _mode(enforce_provider_cap)

    template = get_prompt_template(task_name, version=prompt_version)
    guardrails = build_guardrails(task_name)
    schema_text = format_schema(schema_bundle)

    base_prompt_tokens = (
        estimate_tokens_with(token_estimator, template.system_template)
        + estimate_tokens_with(token_estimator, guardrails)
        + estimate_tokens_with(token_estimator, schema_text)
    )

    if max_context_tokens is not None and base_prompt_tokens > max_context_tokens:
        raise ValueError(
            "Base prompt exceeds provider context cap "
            f"(base_prompt_tokens={base_prompt_tokens} > max_context_tokens={max_context_tokens})."
        )

    budget = allocate_budget(task_name)
    task_input_tokens = estimate_tokens(json.dumps(context_bundle.inputs, ensure_ascii=True, separators=(",", ":")))
    token_warnings: list[str] = []
    if task_input_tokens > budget.max_total:
        msg = (
            "Task input tokens exceed task policy budget "
            f"({task_input_tokens} > {budget.max_total})."
        )
        if enforce_task == "block":
            raise ValueError(msg)
        if enforce_task == "warn":
            token_warnings.append(msg)
    truncation = apply_truncation(
        context_bundle=context_bundle,
        memory_bundle=memory_bundle,
        schema_bundle=schema_bundle,
        budget=budget,
        base_prompt_tokens=0,
    )

    if truncation.aux_context is not None and len(truncation.aux_context) > 0:
        trimmed_inputs = dict(context_bundle.inputs)
        trimmed_inputs["auxiliary_context"] = truncation.aux_context
        context_bundle = LLMContextBundle(
            task_name=context_bundle.task_name,
            inputs=trimmed_inputs,
            constraints=context_bundle.constraints,
            options=context_bundle.options,
            memory=context_bundle.memory,
            metadata=context_bundle.metadata,
        )

    system_message, user_message = assemble_messages(
        template=template,
        context=context_bundle,
        memory=truncation.memory_bundle,
        guardrails=guardrails,
        schema_text=schema_text,
        fewshot_text=truncation.fewshot_text,
        constraints=context_bundle.constraints,
    )
    total_prompt_tokens = estimate_tokens(system_message) + estimate_tokens(user_message)

    if max_context_tokens is not None and base_prompt_tokens > max_context_tokens:
        msg = (
            "Base prompt exceeds provider context cap "
            f"(base_prompt_tokens={base_prompt_tokens} > max_context_tokens={max_context_tokens})."
        )
        if enforce_provider == "block":
            raise ValueError(msg)
        if enforce_provider == "warn":
            token_warnings.append(msg)

    if max_context_tokens is not None and total_prompt_tokens > max_context_tokens:
        provider_budget = allocate_budget(task_name, max_context_tokens=max_context_tokens)
        truncation = apply_truncation(
            context_bundle=context_bundle,
            memory_bundle=truncation.memory_bundle,
            schema_bundle=schema_bundle,
            budget=provider_budget,
            base_prompt_tokens=base_prompt_tokens,
        )
        if truncation.aux_context is not None and len(truncation.aux_context) > 0:
            trimmed_inputs = dict(context_bundle.inputs)
            trimmed_inputs["auxiliary_context"] = truncation.aux_context
            context_bundle = LLMContextBundle(
                task_name=context_bundle.task_name,
                inputs=trimmed_inputs,
                constraints=context_bundle.constraints,
                options=context_bundle.options,
                memory=context_bundle.memory,
                metadata=context_bundle.metadata,
            )
        system_message, user_message = assemble_messages(
            template=template,
            context=context_bundle,
            memory=truncation.memory_bundle,
            guardrails=guardrails,
            schema_text=schema_text,
            fewshot_text=truncation.fewshot_text,
            constraints=context_bundle.constraints,
        )
        total_prompt_tokens = estimate_tokens(system_message) + estimate_tokens(user_message)

    if max_context_tokens is not None and total_prompt_tokens > max_context_tokens:
        msg = (
            "Full prompt exceeds provider context cap "
            f"({total_prompt_tokens} > {max_context_tokens})."
        )
        if enforce_provider == "block":
            raise ValueError(msg)
        if enforce_provider == "warn":
            token_warnings.append(msg)

    prompt_pkg = PromptPackage(
        task_name=task_name,
        template=template,
        schema=schema_bundle,
        metadata={
            "system_message": system_message,
            "user_message": user_message,
            "developer_message": None,
            "prompt_version": template.version,
            "schema_version": schema_bundle.output_schema.get("version") if schema_bundle and schema_bundle.output_schema else None,
        },
    )

    request = ProviderRequest(
        task_name=task_name,
        prompt=user_message,
        context=context_bundle,
        constraints=context_bundle.constraints,
        options=context_bundle.options,
        system_message=system_message,
        user_message=user_message,
        developer_message=None,
        response_format="json",
    )

    raw_response = provider.generate(request)

    parsed = parse_response(
        task_name=task_name,
        raw_response=raw_response,
        schema_bundle=schema_bundle,
        strict_required=strict_required,
    )

    outcome = validate_result(
        parsed,
        ValidationContext(
            task_name=task_name,
            schema_bundle=schema_bundle,
            deterministic_context=deterministic_context,
        ),
    )

    if audit_hook:
        truncation_memory_tokens = None
        if truncation.memory_bundle and truncation.memory_bundle.items:
            truncation_memory_tokens = estimate_tokens(json.dumps(truncation.memory_bundle.items, ensure_ascii=True, separators=(",", ":")))
        truncation_aux_tokens = None
        if truncation.aux_context:
            truncation_aux_tokens = estimate_tokens(json.dumps(truncation.aux_context, ensure_ascii=True, separators=(",", ":")))
        audit_hook(
            {
                "task_name": task_name.value,
                "prompt_version": template.version,
                "schema_version": schema_bundle.output_schema.get("version") if schema_bundle and schema_bundle.output_schema else None,
                "provider": raw_response.provider_name,
                "model": raw_response.model,
                "latency_ms": raw_response.latency_ms,
                "usage": raw_response.usage,
                "validation_decision": outcome.decision,
                "parse_warnings": list(parsed.warnings),
                "token_budget": {
                    "max_total": budget.max_total,
                    "max_fewshot": budget.max_fewshot,
                    "max_memory": budget.max_memory,
                    "max_aux_context": budget.max_aux_context,
                    "base_prompt_tokens": base_prompt_tokens,
                    "provider_context_cap": max_context_tokens,
                },
                "token_truncation": {
                    "fewshot_tokens": estimate_tokens(truncation.fewshot_text),
                    "memory_tokens": truncation_memory_tokens,
                    "aux_context_tokens": truncation_aux_tokens,
                },
                "token_warnings": token_warnings,
                "system_message": system_message,
                "user_message": user_message,
            }
        )

    final_output = parsed.structured if parsed and parsed.structured else None
    return raw_response, context_bundle, memory_bundle, prompt_pkg, parsed, outcome, final_output
