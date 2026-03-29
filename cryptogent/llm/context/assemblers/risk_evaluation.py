from __future__ import annotations

from typing import Any

from cryptogent.llm.context.normalizers import normalize_symbol, normalize_float, strip_empty


def build_risk_evaluation_context(raw: dict[str, Any]) -> dict[str, Any]:
    data = {
        "symbol": normalize_symbol(raw.get("symbol")),
        "position": raw.get("position"),
        "exposure": normalize_float(raw.get("exposure")),
        "drawdown_pct": normalize_float(raw.get("drawdown_pct")),
        "volatility_pct": normalize_float(raw.get("volatility_pct")),
        "liquidity_score": normalize_float(raw.get("liquidity_score")),
        "risk_limits": raw.get("risk_limits"),
        "market_snapshot": raw.get("market_snapshot"),
    }
    data["auxiliary_context"] = {
        "notes": raw.get("notes"),
        "extra": raw.get("extra"),
    }
    return strip_empty(data)
