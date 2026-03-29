from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LLMTaskName(str, Enum):
    INTENT_CLASSIFICATION = "intent_classification"
    
    NEWS_SUMMARY = "news_summary"
    MARKET_SENTIMENT_SYNTHESIS = "market_sentiment_synthesis"
    MARKET_FINAL_ANALYSIS = "market_final_analysis"

    TRADE_RECOMMENDATION = "trade_recommendation"
    TRADE_DECISION = "trade_decision"
    RISK_EVALUATION = "risk_evaluation"
    SAFETY_POLICY_REVIEW = "safety_policy_review"

    POSITION_SUMMARY = "position_summary"
    PORTFOLIO_RISK_SUMMARY = "portfolio_risk_summary"

    DECISION_EXPLANATION = "decision_explanation"


@dataclass(frozen=True)
class TaskConstraints:
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop: tuple[str, ...] = ()
    response_format: str | None = None


@dataclass(frozen=True)
class TaskOptions:
    allow_tools: bool = False
    tool_choice: str | None = None
    timeout_s: float | None = None
    metadata: dict[str, str] | None = None
