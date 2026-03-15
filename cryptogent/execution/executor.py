from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from cryptogent.exchange.binance_errors import BinanceAPIError
from cryptogent.exchange.binance_spot import BinanceSpotClient
from cryptogent.execution.result_parser import ExecutionParseError, FillSummary, parse_fills
from cryptogent.state.manager import StateManager
from cryptogent.util.time import utcnow_iso
from cryptogent.validation.binance_rules import quantize_down


class ExecutionError(RuntimeError):
    pass


def _utc_ts_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def generate_client_order_id(*, candidate_id: int) -> str:
    # Keep short to avoid exchange length limits.
    rand = secrets.token_hex(2)  # 4 chars
    return f"cg_{candidate_id}_{_utc_ts_compact()}_{rand}"


@dataclass(frozen=True)
class ExecutionOutcome:
    local_status: str
    raw_status: str | None
    binance_order_id: str | None
    fills: FillSummary | None
    message: str
    details: dict


def _safe_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def execute_market_buy_quote(
    *,
    execution_client: BinanceSpotClient,
    state: StateManager,
    candidate: dict,
    plan: dict,
    rules_snapshot: dict,
    runtime_environment: str,
) -> tuple[int, ExecutionOutcome]:
    candidate_id = int(candidate["id"])
    plan_id = int(candidate["trade_plan_id"])
    trade_request_id = int(candidate["trade_request_id"])
    symbol = str(candidate["symbol"] or "").strip().upper()
    approved_budget_asset = str(candidate["approved_budget_asset"] or "").strip().upper()
    approved_budget_amount = str(candidate["approved_budget_amount"] or "").strip()

    quote_asset = str(rules_snapshot.get("quote_asset") or "").strip().upper()
    if not quote_asset:
        raise ExecutionError("missing_quote_asset_in_rules_snapshot")
    if approved_budget_asset != quote_asset:
        raise ExecutionError(f"approved_budget_asset_mismatch: {approved_budget_asset} != {quote_asset}")

    client_order_id = generate_client_order_id(candidate_id=candidate_id)
    execution_id = state.create_execution(
        candidate_id=candidate_id,
        plan_id=plan_id,
        trade_request_id=trade_request_id,
        symbol=symbol,
        side="BUY",
        order_type="MARKET_BUY",
        execution_environment=runtime_environment,
        client_order_id=client_order_id,
        quote_order_qty=approved_budget_amount,
    )

    state.append_audit(
        level="INFO",
        event="execution_submitting",
        details={
            "execution_id": execution_id,
            "candidate_id": candidate_id,
            "plan_id": plan_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": "BUY",
            "order_type": "MARKET",
            "execution_environment": runtime_environment,
            "approved_budget": f"{approved_budget_amount} {approved_budget_asset}",
        },
    )

    def _update_uncertain(reason: str, *, retry_count: int) -> None:
        state.update_execution(
            execution_id=execution_id,
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            executed_quantity=None,
            avg_fill_price=None,
            total_quote_spent=None,
            commission_total=None,
            commission_asset=None,
            fills_count=None,
            retry_count=retry_count,
            message=reason,
            details_json=_safe_json({"reason": reason}),
            submitted_at_utc=utcnow_iso(),
            reconciled_at_utc=None,
        )

    def _finalize_from_order(order: dict, *, retry_count: int, note: str) -> ExecutionOutcome:
        raw_status = str(order.get("status") or "") or None
        order_id = str(order.get("orderId") or "") or None
        try:
            fills = parse_fills(order)
        except ExecutionParseError as e:
            fills = None
            note = f"{note}; fill_parse_error={e}"

        local_status = "submitted"
        if raw_status == "FILLED":
            local_status = "filled"
        elif raw_status == "PARTIALLY_FILLED":
            local_status = "partially_filled"

        state.update_execution(
            execution_id=execution_id,
            local_status=local_status,
            raw_status=raw_status,
            binance_order_id=order_id,
            executed_quantity=str(fills.executed_qty) if fills else None,
            avg_fill_price=str(fills.avg_fill_price) if fills and fills.avg_fill_price is not None else None,
            total_quote_spent=str(fills.total_quote_spent) if fills else None,
            commission_total=str(fills.commission_total) if fills and fills.commission_total is not None else None,
            commission_asset=(fills.commission_asset if fills else None),
            fills_count=(fills.fills_count if fills else None),
            retry_count=retry_count,
            message=note,
            details_json=_safe_json(
                {
                    "raw_status": raw_status,
                    "commission_breakdown": fills.commission_breakdown if fills else {},
                    "source": "exchange",
                }
            ),
            submitted_at_utc=utcnow_iso(),
            reconciled_at_utc=utcnow_iso(),
        )

        return ExecutionOutcome(
            local_status=local_status,
            raw_status=raw_status,
            binance_order_id=order_id,
            fills=fills,
            message=note,
            details={"commission_breakdown": fills.commission_breakdown if fills else {}},
        )

    def _reconcile_or_not_found(*, retry_count: int) -> tuple[bool, dict | None]:
        try:
            order = execution_client.get_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
            return True, order
        except BinanceAPIError as e:
            # -2013 is commonly "Order does not exist."
            if e.code == -2013:
                return False, None
            raise

    # First attempt.
    try:
        order = execution_client.create_order_market_buy_quote(
            symbol=symbol, quote_order_qty=approved_budget_amount, client_order_id=client_order_id
        )
        return execution_id, _finalize_from_order(order, retry_count=0, note="submitted")
    except BinanceAPIError as e:
        if e.status != 0:
            state.update_execution(
                execution_id=execution_id,
                local_status="failed",
                raw_status=None,
                binance_order_id=None,
                executed_quantity=None,
                avg_fill_price=None,
                total_quote_spent=None,
                commission_total=None,
                commission_asset=None,
                fills_count=None,
                retry_count=0,
                message=str(e),
                details_json=_safe_json({"error": str(e)}),
                submitted_at_utc=utcnow_iso(),
                reconciled_at_utc=utcnow_iso(),
            )
            return execution_id, ExecutionOutcome(
                local_status="failed",
                raw_status=None,
                binance_order_id=None,
                fills=None,
                message=str(e),
                details={"error": str(e)},
            )

        # Transport-level unknown: uncertain + reconcile + (maybe) retry once.
        _update_uncertain(str(e), retry_count=0)

    # Reconcile before retry.
    try:
        found, order = _reconcile_or_not_found(retry_count=0)
        if found and order is not None:
            return execution_id, _finalize_from_order(order, retry_count=0, note="reconciled_after_timeout")
    except BinanceAPIError as e:
        _update_uncertain(f"reconcile_failed: {e}", retry_count=0)
        return execution_id, ExecutionOutcome(
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            fills=None,
            message=f"reconcile_failed: {e}",
            details={"error": str(e)},
        )

    # Retry once with same client_order_id.
    try:
        order = execution_client.create_order_market_buy_quote(
            symbol=symbol, quote_order_qty=approved_budget_amount, client_order_id=client_order_id
        )
        return execution_id, _finalize_from_order(order, retry_count=1, note="submitted_after_retry")
    except BinanceAPIError as e:
        # After retry limit, remain uncertain (fail-closed).
        _update_uncertain(f"retry_failed: {e}", retry_count=1)
        return execution_id, ExecutionOutcome(
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            fills=None,
            message=f"retry_failed: {e}",
            details={"error": str(e)},
        )


def execute_limit_buy(
    *,
    execution_client: BinanceSpotClient,
    state: StateManager,
    candidate: dict,
    plan: dict,
    rules_snapshot: dict,
    runtime_environment: str,
) -> tuple[int, ExecutionOutcome]:
    candidate_id = int(candidate["id"])
    plan_id = int(candidate["trade_plan_id"])
    trade_request_id = int(candidate["trade_request_id"])
    symbol = str(candidate["symbol"] or "").strip().upper()
    approved_budget_asset = str(candidate["approved_budget_asset"] or "").strip().upper()
    approved_budget_amount = Decimal(str(candidate["approved_budget_amount"] or "0"))

    limit_price_s = candidate.get("limit_price")
    if limit_price_s in (None, ""):
        raise ExecutionError("missing_limit_price")
    limit_price_raw = Decimal(str(limit_price_s))

    quote_asset = str(rules_snapshot.get("quote_asset") or "").strip().upper()
    if not quote_asset:
        raise ExecutionError("missing_quote_asset_in_rules_snapshot")
    if approved_budget_asset != quote_asset:
        raise ExecutionError(f"approved_budget_asset_mismatch: {approved_budget_asset} != {quote_asset}")

    tick_size_s = rules_snapshot.get("tick_size")
    step_size_s = rules_snapshot.get("step_size")
    min_qty_s = rules_snapshot.get("min_qty")
    max_qty_s = rules_snapshot.get("max_qty")
    min_notional_s = rules_snapshot.get("min_notional")
    if not (tick_size_s and step_size_s and min_qty_s and max_qty_s and min_notional_s):
        raise ExecutionError("missing_rules_snapshot_fields_for_limit_buy")

    tick_size = Decimal(str(tick_size_s))
    step_size = Decimal(str(step_size_s))
    min_qty = Decimal(str(min_qty_s))
    max_qty = Decimal(str(max_qty_s))
    min_notional = Decimal(str(min_notional_s))
    if tick_size <= 0 or step_size <= 0:
        raise ExecutionError("invalid_tick_or_step_size")

    limit_price = quantize_down(limit_price_raw, tick_size)
    if limit_price <= 0:
        raise ExecutionError("limit_price_rounded_non_positive")

    raw_qty = approved_budget_amount / limit_price
    qty = quantize_down(raw_qty, step_size)
    if qty <= 0:
        raise ExecutionError("quantity_rounded_to_zero")
    if qty < min_qty:
        raise ExecutionError(f"qty_below_minQty:{qty}<{min_qty}")
    if qty > max_qty:
        raise ExecutionError(f"qty_above_maxQty:{qty}>{max_qty}")
    notional = qty * limit_price
    if notional < min_notional:
        raise ExecutionError(f"min_notional_failed:{notional}<{min_notional}")

    client_order_id = generate_client_order_id(candidate_id=candidate_id)
    time_in_force = "GTC"
    execution_id = state.create_execution(
        candidate_id=candidate_id,
        plan_id=plan_id,
        trade_request_id=trade_request_id,
        symbol=symbol,
        side="BUY",
        order_type="LIMIT_BUY",
        execution_environment=runtime_environment,
        client_order_id=client_order_id,
        quote_order_qty=str(approved_budget_amount),
        limit_price=str(limit_price),
        time_in_force=time_in_force,
        requested_quantity=str(qty),
    )

    state.append_audit(
        level="INFO",
        event="execution_submitting",
        details={
            "execution_id": execution_id,
            "candidate_id": candidate_id,
            "plan_id": plan_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": "BUY",
            "order_type": "LIMIT",
            "execution_environment": runtime_environment,
            "price": str(limit_price),
            "quantity": str(qty),
            "approved_budget": f"{approved_budget_amount} {approved_budget_asset}",
        },
    )

    def _update_uncertain(reason: str, *, retry_count: int) -> None:
        state.update_execution(
            execution_id=execution_id,
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            executed_quantity=None,
            avg_fill_price=None,
            total_quote_spent=None,
            commission_total=None,
            commission_asset=None,
            fills_count=None,
            retry_count=retry_count,
            message=reason,
            details_json=_safe_json({"reason": reason}),
            submitted_at_utc=utcnow_iso(),
            reconciled_at_utc=None,
        )

    def _finalize_from_order(order: dict, *, retry_count: int, note: str) -> ExecutionOutcome:
        raw_status = str(order.get("status") or "") or None
        order_id = str(order.get("orderId") or "") or None
        try:
            fills = parse_fills(order)
        except ExecutionParseError as e:
            fills = None
            note = f"{note}; fill_parse_error={e}"

        local_status = "submitted"
        if raw_status in ("NEW",):
            local_status = "open"
        elif raw_status == "FILLED":
            local_status = "filled"
        elif raw_status == "PARTIALLY_FILLED":
            local_status = "partially_filled"
        elif raw_status in ("CANCELED", "CANCELLED"):
            local_status = "cancelled"
        elif raw_status in ("EXPIRED",):
            local_status = "expired"

        state.update_execution(
            execution_id=execution_id,
            local_status=local_status,
            raw_status=raw_status,
            binance_order_id=order_id,
            executed_quantity=str(fills.executed_qty) if fills else None,
            avg_fill_price=str(fills.avg_fill_price) if fills and fills.avg_fill_price is not None else None,
            total_quote_spent=str(fills.total_quote_spent) if fills else None,
            commission_total=str(fills.commission_total) if fills and fills.commission_total is not None else None,
            commission_asset=(fills.commission_asset if fills else None),
            fills_count=(fills.fills_count if fills else None),
            retry_count=retry_count,
            message=note,
            details_json=_safe_json(
                {
                    "raw_status": raw_status,
                    "commission_breakdown": fills.commission_breakdown if fills else {},
                    "source": "exchange",
                }
            ),
            submitted_at_utc=utcnow_iso(),
            reconciled_at_utc=utcnow_iso(),
        )

        return ExecutionOutcome(
            local_status=local_status,
            raw_status=raw_status,
            binance_order_id=order_id,
            fills=fills,
            message=note,
            details={"commission_breakdown": fills.commission_breakdown if fills else {}},
        )

    def _reconcile_or_not_found() -> tuple[bool, dict | None]:
        try:
            order = execution_client.get_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
            return True, order
        except BinanceAPIError as e:
            if e.code == -2013:
                return False, None
            raise

    try:
        order = execution_client.create_order_limit_buy(
            symbol=symbol,
            price=str(limit_price),
            quantity=str(qty),
            client_order_id=client_order_id,
            time_in_force=time_in_force,
        )
        return execution_id, _finalize_from_order(order, retry_count=0, note="submitted")
    except BinanceAPIError as e:
        if e.status != 0:
            state.update_execution(
                execution_id=execution_id,
                local_status="failed",
                raw_status=None,
                binance_order_id=None,
                executed_quantity=None,
                avg_fill_price=None,
                total_quote_spent=None,
                commission_total=None,
                commission_asset=None,
                fills_count=None,
                retry_count=0,
                message=str(e),
                details_json=_safe_json({"error": str(e)}),
                submitted_at_utc=utcnow_iso(),
                reconciled_at_utc=utcnow_iso(),
            )
            return execution_id, ExecutionOutcome(
                local_status="failed",
                raw_status=None,
                binance_order_id=None,
                fills=None,
                message=str(e),
                details={"error": str(e)},
            )
        _update_uncertain(str(e), retry_count=0)

    try:
        found, order = _reconcile_or_not_found()
        if found and order is not None:
            return execution_id, _finalize_from_order(order, retry_count=0, note="reconciled_after_timeout")
    except BinanceAPIError as e:
        _update_uncertain(f"reconcile_failed: {e}", retry_count=0)
        return execution_id, ExecutionOutcome(
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            fills=None,
            message=f"reconcile_failed: {e}",
            details={"error": str(e)},
        )

    try:
        order = execution_client.create_order_limit_buy(
            symbol=symbol,
            price=str(limit_price),
            quantity=str(qty),
            client_order_id=client_order_id,
            time_in_force=time_in_force,
        )
        return execution_id, _finalize_from_order(order, retry_count=1, note="submitted_after_retry")
    except BinanceAPIError as e:
        _update_uncertain(f"retry_failed: {e}", retry_count=1)
        return execution_id, ExecutionOutcome(
            local_status="uncertain_submitted",
            raw_status=None,
            binance_order_id=None,
            fills=None,
            message=f"retry_failed: {e}",
            details={"error": str(e)},
        )
