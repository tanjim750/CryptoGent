from __future__ import annotations

from typing import Any

from cryptogent.llm.context.normalizers import normalize_symbol, normalize_symbols, strip_empty


def build_news_summary_context(raw: dict[str, Any]) -> dict[str, Any]:
    data = {
        "headline": raw.get("headline") or raw.get("title"),
        "source": raw.get("source"),
        "published_at": raw.get("published_at") or raw.get("published_at_utc"),
        "symbols": normalize_symbols(raw.get("symbols") or raw.get("tickers")),
        "primary_symbol": normalize_symbol(raw.get("primary_symbol") or raw.get("symbol")),
        "body": raw.get("body") or raw.get("content") or raw.get("text"),
        "language": raw.get("language"),
        "url": raw.get("url"),
    }
    return strip_empty(data)
