from __future__ import annotations

import json

from dataclasses import dataclass

from cryptogent.llm.contracts import LLMContextBundle, MemoryBundle, SchemaBundle
from cryptogent.llm.prompts.fewshot import build_fewshot
from cryptogent.llm.token_policy.context_budgeter import BudgetAllocation
from cryptogent.llm.token_policy.token_estimator import estimate_tokens


@dataclass(frozen=True)
class TruncationResult:
    fewshot_text: str
    memory_bundle: MemoryBundle | None
    aux_context: dict[str, object]


def apply_truncation(
    *,
    context_bundle: LLMContextBundle,
    memory_bundle: MemoryBundle | None,
    schema_bundle: SchemaBundle | None,
    budget: BudgetAllocation,
    base_prompt_tokens: int = 0,
) -> TruncationResult:
    max_fewshot = max(0, budget.max_fewshot - base_prompt_tokens)
    max_memory = max(0, budget.max_memory - base_prompt_tokens)
    max_aux = max(0, budget.max_aux_context - base_prompt_tokens)

    fewshot_text = build_fewshot(schema_bundle)
    fewshot_text = _trim_text(fewshot_text, max_fewshot)

    memory_bundle = _trim_memory(memory_bundle, max_memory)
    aux_context = _trim_aux_context(context_bundle.inputs, max_aux)

    return TruncationResult(
        fewshot_text=fewshot_text,
        memory_bundle=memory_bundle,
        aux_context=aux_context,
    )


def _trim_text(text: str, max_tokens: int) -> str:
    if not text:
        return ""
    if estimate_tokens(text) <= max_tokens:
        return text
    # naive trim by characters
    max_chars = max_tokens * 4
    return text[:max_chars]


def _trim_memory(memory_bundle: MemoryBundle | None, max_tokens: int) -> MemoryBundle | None:
    if memory_bundle is None:
        return None
    if not memory_bundle.items:
        return memory_bundle
    items = list(memory_bundle.items)
    kept: list[dict[str, object]] = []
    for item in items:
        candidate = kept + [item]
        text = json.dumps(candidate, ensure_ascii=True, separators=(",", ":"))
        if estimate_tokens(text) > max_tokens:
            break
        kept.append(item)
    return MemoryBundle(items=tuple(kept), source=memory_bundle.source, metadata=memory_bundle.metadata)


def _trim_aux_context(inputs: dict[str, object], max_tokens: int) -> dict[str, object]:
    aux = inputs.get("auxiliary_context")
    if not isinstance(aux, dict):
        return {}
    text = json.dumps(aux, ensure_ascii=True, separators=(",", ":"))
    if estimate_tokens(text) <= max_tokens:
        return aux
    max_chars = max_tokens * 4
    trimmed = text[:max_chars]
    try:
        return json.loads(trimmed)
    except Exception:
        return {}
