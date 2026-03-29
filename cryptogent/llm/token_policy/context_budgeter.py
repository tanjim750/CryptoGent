from __future__ import annotations

from dataclasses import dataclass

from cryptogent.llm.contracts import LLMTaskName
from cryptogent.llm.token_policy.policies import get_policy


@dataclass(frozen=True)
class BudgetAllocation:
    max_total: int
    max_fewshot: int
    max_memory: int
    max_aux_context: int


def allocate_budget(task_name: LLMTaskName, *, max_context_tokens: int | None = None) -> BudgetAllocation:
    policy = get_policy(task_name)
    max_total = max(0, policy.max_tokens)
    if max_context_tokens is not None:
        max_total = min(max_total, max(0, max_context_tokens))
    max_fewshot = int(max_total * 0.10)
    max_memory = int(max_total * 0.20)
    max_aux_context = int(max_total * 0.20)
    return BudgetAllocation(
        max_total=max_total,
        max_fewshot=max_fewshot,
        max_memory=max_memory,
        max_aux_context=max_aux_context,
    )
