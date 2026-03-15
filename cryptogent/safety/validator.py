from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from cryptogent.exchange.binance_errors import BinanceAPIError
from cryptogent.exchange.binance_spot import BinanceSpotClient
from cryptogent.state.manager import StateManager
from cryptogent.util.time import utcnow_iso


class SafetyError(RuntimeError):
    pass


def _d(value: object, name: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise SafetyError(f"Invalid decimal for {name}") from e
    if d.is_nan() or d.is_infinite():
        raise SafetyError(f"Invalid decimal for {name}")
    return d


def _parse_iso_utc(s: str, name: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as e:
        raise SafetyError(f"Invalid {name}") from e


def _pct(numer: Decimal, denom: Decimal) -> Decimal:
    if denom == 0:
        return Decimal("0")
    return (numer / denom) * Decimal("100")


def _json_load(s: object, name: str) -> dict:
    if not s:
        raise SafetyError(f"Missing {name}")
    try:
        obj = json.loads(str(s))
    except Exception as e:
        raise SafetyError(f"Invalid JSON for {name}") from e
    if not isinstance(obj, dict):
        raise SafetyError(f"Expected object for {name}")
    return obj


@dataclass(frozen=True)
class SafetyDecision:
    category: str  # safe | safe_with_warning | unsafe | expired
    validation_status: str  # passed | failed | passed_with_adjustments
    risk_status: str  # approved | approved_with_warning | rejected
    approved_budget_asset: str
    approved_budget_amount: Decimal
    approved_quantity: Decimal
    summary: str
    warnings: list[str]
    errors: list[str]
    details: dict
    created_at_utc: str


def evaluate_safety(
    *,
    state: StateManager,
    execution_client: BinanceSpotClient,
    plan: dict,
    trade_request: dict,
    order_type: str,
    limit_price: Decimal | None,
    max_plan_age_minutes: int,
    max_price_drift_warning_pct: Decimal,
    max_price_drift_unsafe_pct: Decimal,
    max_position_pct: Decimal,
    max_stop_loss_pct: Decimal,
) -> SafetyDecision:
    errors: list[str] = []
    warnings: list[str] = []

    created_at_utc_s = str(plan.get("created_at_utc") or "")
    created_at = _parse_iso_utc(created_at_utc_s, "plan.created_at_utc")
    age_min = Decimal(str((datetime.now(UTC) - created_at).total_seconds())) / Decimal("60")
    if age_min > Decimal(str(max_plan_age_minutes)):
        return SafetyDecision(
            category="expired",
            validation_status="failed",
            risk_status="rejected",
            approved_budget_asset=str(plan.get("approved_budget_asset") or ""),
            approved_budget_amount=_d(plan.get("approved_budget_amount") or "0", "approved_budget_amount"),
            approved_quantity=_d(plan.get("rounded_quantity") or "0", "rounded_quantity"),
            summary=f"Plan expired (age_minutes={age_min:.2f} > {max_plan_age_minutes})",
            warnings=[],
            errors=["plan_expired"],
            details={"plan_age_minutes": str(age_min), "max_plan_age_minutes": max_plan_age_minutes},
            created_at_utc=utcnow_iso(),
        )

    # Fail-closed required fields.
    symbol = str(plan.get("symbol") or "").strip().upper()
    if not symbol:
        errors.append("missing_symbol")
    approved_budget_asset = str(plan.get("approved_budget_asset") or "").strip().upper()
    if not approved_budget_asset:
        errors.append("missing_approved_budget_asset")

    qty_s = plan.get("rounded_quantity")
    budget_s = plan.get("approved_budget_amount")
    if qty_s in (None, ""):
        errors.append("missing_approved_quantity")
    if budget_s in (None, ""):
        errors.append("missing_approved_budget_amount")
    rules_snapshot = None
    try:
        rules_snapshot = _json_load(plan.get("rules_snapshot_json"), "rules_snapshot_json")
    except SafetyError as e:
        errors.append(str(e))

    if errors:
        return SafetyDecision(
            category="unsafe",
            validation_status="failed",
            risk_status="rejected",
            approved_budget_asset=approved_budget_asset or "-",
            approved_budget_amount=Decimal("0"),
            approved_quantity=Decimal("0"),
            summary="Unsafe: missing required plan fields",
            warnings=warnings,
            errors=errors,
            details={"plan_id": plan.get("id"), "errors": errors},
            created_at_utc=utcnow_iso(),
        )

    approved_budget_amount = _d(budget_s, "approved_budget_amount")
    approved_quantity = _d(qty_s, "rounded_quantity")

    # Deterministic validation against stored rules snapshot.
    step_size = _d(rules_snapshot.get("step_size"), "step_size")
    min_notional = _d(rules_snapshot.get("min_notional"), "min_notional")
    price = _d(plan.get("price"), "plan.price")
    expected_notional = _d(plan.get("expected_notional") or (approved_quantity * price), "expected_notional")

    ot = (order_type or "").strip().upper()
    if ot not in ("MARKET_BUY", "LIMIT_BUY"):
        errors.append("invalid_order_type")
    if ot == "LIMIT_BUY":
        if limit_price is None:
            errors.append("missing_limit_price")
        else:
            if limit_price <= 0:
                errors.append("invalid_limit_price")

    if step_size <= 0:
        errors.append("invalid_step_size")
    if approved_quantity <= 0:
        errors.append("quantity_non_positive")
    if min_notional <= 0:
        errors.append("invalid_min_notional")
    if expected_notional < min_notional:
        errors.append("min_notional_failed")

    # Step alignment check: qty must be multiple of step_size.
    if step_size > 0 and approved_quantity > 0:
        steps = (approved_quantity / step_size).to_integral_value()
        if steps * step_size != approved_quantity:
            errors.append("quantity_step_mismatch")

    # Risk rules from trade request.
    pt = _d(trade_request.get("profit_target_pct"), "profit_target_pct")
    sl = _d(trade_request.get("stop_loss_pct"), "stop_loss_pct")
    if sl <= 0:
        errors.append("missing_or_invalid_stop_loss")
    if sl > max_stop_loss_pct:
        errors.append("stop_loss_too_large")
    if sl >= pt:
        warnings.append("stop_loss_ge_profit_target")

    # Active position policy: one active position at a time.
    active = state.get_active_position()
    if active:
        errors.append("active_position_exists")

    # Live rechecks (fail-closed).
    try:
        info = execution_client.get_symbol_info(symbol=symbol)
        if not info:
            errors.append("symbol_not_found_live")
        else:
            status = str(info.get("status") or "")
            if status != "TRADING":
                errors.append(f"symbol_not_trading:{status}")
    except (BinanceAPIError, ValueError) as e:
        errors.append(f"live_symbol_check_failed:{e}")

    try:
        live_price = _d(execution_client.get_ticker_price(symbol=symbol), "live_price")
        drift = _pct(abs(live_price - price), price if price != 0 else live_price)
        if drift >= max_price_drift_unsafe_pct:
            errors.append(f"price_drift_unsafe:{drift}")
        elif drift >= max_price_drift_warning_pct:
            warnings.append(f"price_drift_warning:{drift}")
    except (BinanceAPIError, SafetyError) as e:
        errors.append(f"live_price_check_failed:{e}")

    try:
        acct = execution_client.get_account()
        balances = acct.get("balances", [])
        free = Decimal("0")
        if isinstance(balances, list):
            for b in balances:
                if isinstance(b, dict) and str(b.get("asset") or "").upper() == approved_budget_asset:
                    free = _d(b.get("free") or "0", "account.free")
                    break
        if approved_budget_amount > free:
            errors.append("insufficient_free_balance")
        if free > 0:
            pct = _pct(approved_budget_amount, free)
            if pct > max_position_pct:
                errors.append("max_position_pct_exceeded")
    except (BinanceAPIError, SafetyError) as e:
        errors.append(f"live_balance_check_failed:{e}")

    if errors:
        return SafetyDecision(
            category="unsafe",
            validation_status="failed",
            risk_status="rejected",
            approved_budget_asset=approved_budget_asset,
            approved_budget_amount=approved_budget_amount,
            approved_quantity=approved_quantity,
            summary="Unsafe: one or more safety checks failed",
            warnings=warnings,
            errors=errors,
            details={"symbol": symbol, "warnings": warnings, "errors": errors},
            created_at_utc=utcnow_iso(),
        )

    if warnings:
        return SafetyDecision(
            category="safe_with_warning",
            validation_status="passed",
            risk_status="approved_with_warning",
            approved_budget_asset=approved_budget_asset,
            approved_budget_amount=approved_budget_amount,
            approved_quantity=approved_quantity,
            summary="Safe with warnings",
            warnings=warnings,
            errors=[],
            details={"symbol": symbol, "warnings": warnings},
            created_at_utc=utcnow_iso(),
        )

    return SafetyDecision(
        category="safe",
        validation_status="passed",
        risk_status="approved",
        approved_budget_asset=approved_budget_asset,
        approved_budget_amount=approved_budget_amount,
        approved_quantity=approved_quantity,
        summary="Safe to proceed to execution",
        warnings=[],
        errors=[],
        details={"symbol": symbol},
        created_at_utc=utcnow_iso(),
    )
