from __future__ import annotations

from typing import Any

from cryptogent.llm.context.assemblers.market_analysis import build_market_analysis_context


def build_market_sentiment_context(raw: dict[str, Any]) -> dict[str, Any]:
    return build_market_analysis_context(raw)
