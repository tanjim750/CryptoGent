from __future__ import annotations

from typing import Any

from cryptogent.llm.context.assemblers.risk_evaluation import build_risk_evaluation_context


def build_portfolio_risk_summary_context(raw: dict[str, Any]) -> dict[str, Any]:
    return build_risk_evaluation_context(raw)
