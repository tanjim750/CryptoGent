from __future__ import annotations

from dataclasses import dataclass

from cryptogent.llm.contracts import LLMTaskName


@dataclass(frozen=True)
class MemoryPolicy:
    enabled: bool = True
    max_items: int | None = None
    recency_days: int | None = 7
    min_score: float | None = None
    policy_name: str = "default_v1"


DEFAULT_POLICY = MemoryPolicy(max_items=None, recency_days=7)


TASK_POLICIES: dict[LLMTaskName, MemoryPolicy] = {
    LLMTaskName.MARKET_FINAL_ANALYSIS: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.TRADE_DECISION: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.RISK_EVALUATION: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.MARKET_SENTIMENT_SYNTHESIS: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.TRADE_RECOMMENDATION: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.POSITION_SUMMARY: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.PORTFOLIO_RISK_SUMMARY: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.SAFETY_POLICY_REVIEW: MemoryPolicy(enabled=True, max_items=5, recency_days=7),
    LLMTaskName.DECISION_EXPLANATION: MemoryPolicy(enabled=True, max_items=3, recency_days=3),
    LLMTaskName.NEWS_SUMMARY: MemoryPolicy(enabled=False),
    LLMTaskName.INTENT_CLASSIFICATION: MemoryPolicy(enabled=False),
}


def get_policy(task_name: LLMTaskName) -> MemoryPolicy:
    return TASK_POLICIES.get(task_name, DEFAULT_POLICY)
