from __future__ import annotations

from typing import Any, Iterable


def normalize_symbol(value: str | None) -> str | None:
    if value is None:
        return None
    sym = str(value).strip().upper()
    return sym or None


def normalize_symbols(values: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        sym = normalize_symbol(values)
        return [sym] if sym else []
    if isinstance(values, Iterable):
        out: list[str] = []
        for v in values:
            sym = normalize_symbol(v)
            if sym:
                out.append(sym)
        return out
    return []


def normalize_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def strip_empty(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, dict):
            nested = strip_empty(v)
            if not nested:
                continue
            out[k] = nested
            continue
        if isinstance(v, (list, tuple)):
            filtered = [item for item in v if item is not None and (not isinstance(item, str) or item.strip())]
            if len(filtered) == 0:
                continue
            out[k] = filtered
            continue
        out[k] = v
    return out
