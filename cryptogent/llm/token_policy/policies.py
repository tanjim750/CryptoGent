from __future__ import annotations

from dataclasses import dataclass

from cryptogent.llm.contracts import LLMTaskName


@dataclass(frozen=True)
class TokenPolicy:
    max_tokens: int


DEFAULT_POLICY = TokenPolicy(max_tokens=1000)


TASK_POLICIES: dict[LLMTaskName, TokenPolicy] = {
    LLMTaskName.NEWS_SUMMARY: TokenPolicy(max_tokens=600),
    LLMTaskName.RISK_EVALUATION: TokenPolicy(max_tokens=800),
    LLMTaskName.TRADE_DECISION: TokenPolicy(max_tokens=1200),
    LLMTaskName.MARKET_FINAL_ANALYSIS: TokenPolicy(max_tokens=1400),
}


def get_policy(task_name: LLMTaskName) -> TokenPolicy:
    return TASK_POLICIES.get(task_name, DEFAULT_POLICY)
