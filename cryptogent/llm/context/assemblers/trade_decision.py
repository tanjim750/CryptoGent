from __future__ import annotations

from typing import Any

from cryptogent.llm.context.normalizers import normalize_symbol, normalize_float, strip_empty


def build_trade_decision_context(raw: dict[str, Any]) -> dict[str, Any]:
    data = {
        "symbol": normalize_symbol(raw.get("symbol") or raw.get("preferred_symbol")),
        "exit_asset": raw.get("exit_asset"),
        "budget_asset": raw.get("budget_asset"),
        "budget_amount": normalize_float(raw.get("budget_amount") or raw.get("budget")),
        "profit_target_pct": normalize_float(raw.get("profit_target_pct")),
        "stop_loss_pct": normalize_float(raw.get("stop_loss_pct")),
        "deadline_utc": raw.get("deadline_utc") or raw.get("deadline"),
        "market_snapshot": raw.get("market_snapshot"),
        "risk_summary": raw.get("risk_summary"),
        "constraints": raw.get("constraints"),
    }
    data["auxiliary_context"] = {
        "notes": raw.get("notes"),
        "extra": raw.get("extra"),
    }
    return strip_empty(data)
