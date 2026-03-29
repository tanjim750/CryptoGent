from __future__ import annotations

from typing import Any

from cryptogent.llm.context.assemblers.trade_decision import build_trade_decision_context


def build_decision_explanation_context(raw: dict[str, Any]) -> dict[str, Any]:
    return build_trade_decision_context(raw)
