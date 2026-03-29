from __future__ import annotations

from typing import Any

from cryptogent.llm.context.normalizers import normalize_symbol, normalize_symbols, normalize_float, strip_empty


def build_market_analysis_context(raw: dict[str, Any]) -> dict[str, Any]:
    data = {
        "symbol": normalize_symbol(raw.get("symbol")),
        "symbols": normalize_symbols(raw.get("symbols")),
        "as_of": raw.get("as_of") or raw.get("as_of_utc"),
        "price": normalize_float(raw.get("price")),
        "price_change_pct": normalize_float(raw.get("price_change_pct")),
        "volume_24h": normalize_float(raw.get("volume_24h")),
        "volatility_pct": normalize_float(raw.get("volatility_pct")),
        "trend": raw.get("trend"),
        "momentum": raw.get("momentum"),
        "sentiment": raw.get("sentiment"),
        "news_summary": raw.get("news_summary"),
        "indicators": raw.get("indicators") or {},
    }
    data["auxiliary_context"] = {
        "warnings": raw.get("warnings") or [],
        "notes": raw.get("notes"),
    }
    return strip_empty(data)
