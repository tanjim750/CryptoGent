from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .policies import MemoryPolicy


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def filter_by_recency(
    items: list[dict[str, Any]], days: int | None, *, drop_missing_timestamps: bool = True
) -> list[dict[str, Any]]:
    if days is None:
        return items
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    kept: list[dict[str, Any]] = []
    for item in items:
        ts = _parse_timestamp(item.get("timestamp") or item.get("created_at") or item.get("created_at_utc"))
        if ts is None:
            if not drop_missing_timestamps:
                kept.append(item)
            continue
        if ts >= cutoff:
            kept.append(item)
    return kept


def filter_by_score(items: list[dict[str, Any]], min_score: float | None) -> list[dict[str, Any]]:
    if min_score is None:
        return items
    kept: list[dict[str, Any]] = []
    for item in items:
        score = item.get("score")
        try:
            score_f = float(score) if score is not None else None
        except Exception:
            score_f = None
        if score_f is None or score_f >= min_score:
            kept.append(item)
    return kept


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("id") or item.get("key") or item.get("hash") or item.get("title") or item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def limit_items(items: list[dict[str, Any]], max_items: int | None) -> list[dict[str, Any]]:
    if not max_items or max_items <= 0:
        return items
    return items[:max_items]


def filter_memory(items: list[dict[str, Any]], policy: MemoryPolicy) -> list[dict[str, Any]]:
    filtered = filter_by_recency(items, policy.recency_days, drop_missing_timestamps=True)
    filtered = filter_by_score(filtered, policy.min_score)
    filtered = dedupe_items(filtered)
    filtered = limit_items(filtered, policy.max_items)
    return filtered
