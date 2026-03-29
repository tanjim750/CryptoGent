from __future__ import annotations

from typing import Any

from cryptogent.llm.contracts import LLMContextBundle, LLMTaskName, MemoryBundle, TaskConstraints, TaskOptions
from cryptogent.llm.context.normalizers import strip_empty
from cryptogent.llm.context.assemblers import (
    build_decision_explanation_context,
    build_market_analysis_context,
    build_market_sentiment_context,
    build_news_summary_context,
    build_portfolio_risk_summary_context,
    build_position_summary_context,
    build_risk_evaluation_context,
    build_safety_policy_context,
    build_trade_decision_context,
    build_trade_recommendation_context,
)


class ContextManager:
    def build(
        self,
        *,
        task_name: LLMTaskName,
        raw_inputs: dict[str, Any],
        constraints: TaskConstraints | None = None,
        options: TaskOptions | None = None,
        memory: MemoryBundle | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMContextBundle:
        constraints = constraints or TaskConstraints()
        options = options or TaskOptions()
        raw_inputs = raw_inputs or {}

        if task_name == LLMTaskName.NEWS_SUMMARY:
            inputs = build_news_summary_context(raw_inputs)
        elif task_name == LLMTaskName.MARKET_SENTIMENT_SYNTHESIS:
            inputs = build_market_sentiment_context(raw_inputs)
        elif task_name == LLMTaskName.MARKET_FINAL_ANALYSIS:
            inputs = build_market_analysis_context(raw_inputs)
        elif task_name == LLMTaskName.TRADE_RECOMMENDATION:
            inputs = build_trade_recommendation_context(raw_inputs)
        elif task_name == LLMTaskName.TRADE_DECISION:
            inputs = build_trade_decision_context(raw_inputs)
        elif task_name == LLMTaskName.RISK_EVALUATION:
            inputs = build_risk_evaluation_context(raw_inputs)
        elif task_name == LLMTaskName.SAFETY_POLICY_REVIEW:
            inputs = build_safety_policy_context(raw_inputs)
        elif task_name == LLMTaskName.POSITION_SUMMARY:
            inputs = build_position_summary_context(raw_inputs)
        elif task_name == LLMTaskName.PORTFOLIO_RISK_SUMMARY:
            inputs = build_portfolio_risk_summary_context(raw_inputs)
        elif task_name == LLMTaskName.DECISION_EXPLANATION:
            inputs = build_decision_explanation_context(raw_inputs)
        else:
            inputs = raw_inputs

        inputs = strip_empty(inputs)

        if memory is not None and not isinstance(memory, MemoryBundle):
            raise TypeError("memory must be a MemoryBundle or None")

        return LLMContextBundle(
            task_name=task_name,
            inputs=inputs,
            constraints=constraints,
            options=options,
            memory=memory,
            metadata=metadata,
        )
