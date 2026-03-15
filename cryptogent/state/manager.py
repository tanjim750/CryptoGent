from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from cryptogent.exchange.interfaces import Balance
from cryptogent.util.time import utcnow_iso
from cryptogent.validation.trade_request import ValidatedTradeRequest


@dataclass(frozen=True)
class OrderRow:
    exchange_order_id: str | None
    symbol: str
    side: str
    type: str
    status: str
    time_in_force: str | None
    price: str | None
    quantity: str
    filled_quantity: str
    executed_quantity: str | None
    created_at_utc: str
    updated_at_utc: str


class StateManager:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def record_sync_run_start(self, *, kind: str) -> int:
        self.ensure_system_state()
        started_at = utcnow_iso()
        cur = self._conn.execute(
            "INSERT INTO sync_runs(kind, started_at_utc, status) VALUES(?, ?, ?)",
            (kind, started_at, "running"),
        )
        return int(cur.lastrowid)

    def record_sync_run_finish(self, *, sync_run_id: int, status: str, error_msg: str | None = None) -> None:
        self.ensure_system_state()
        finished_at = utcnow_iso()
        self._conn.execute(
            "UPDATE sync_runs SET finished_at_utc = ?, status = ?, error_msg = ? WHERE id = ?",
            (finished_at, status, error_msg, sync_run_id),
        )
        if status == "ok":
            self._conn.execute(
                "UPDATE system_state SET last_successful_sync_time_utc = ?, updated_at_utc = ? WHERE id = 1",
                (finished_at, finished_at),
            )

    def ensure_system_state(self) -> None:
        now = utcnow_iso()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO system_state(id, created_at_utc, updated_at_utc)
            VALUES(1, ?, ?)
            """,
            (now, now),
        )
        # Best-effort backfill for existing DBs created before system_state existed.
        self._conn.execute(
            """
            UPDATE system_state
            SET last_successful_sync_time_utc = (
              SELECT MAX(finished_at_utc) FROM sync_runs WHERE status = 'ok' AND finished_at_utc IS NOT NULL
            ),
            updated_at_utc = ?
            WHERE id = 1 AND last_successful_sync_time_utc IS NULL
            """,
            (now,),
        )

    def update_system_start(self, *, current_mode: str) -> None:
        now = utcnow_iso()
        self.ensure_system_state()
        self._conn.execute(
            """
            UPDATE system_state
            SET last_start_time_utc = ?,
                current_mode = ?,
                updated_at_utc = ?
            WHERE id = 1
            """,
            (now, current_mode, now),
        )

    def update_system_shutdown(self) -> None:
        now = utcnow_iso()
        self.ensure_system_state()
        self._conn.execute(
            "UPDATE system_state SET last_shutdown_time_utc = ?, updated_at_utc = ? WHERE id = 1",
            (now, now),
        )

    def get_system_state(self) -> dict | None:
        self.ensure_system_state()
        cur = self._conn.execute("SELECT * FROM system_state WHERE id = 1")
        row = cur.fetchone()
        return dict(row) if row else None

    def append_audit(self, *, level: str, event: str, details: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO audit_logs(created_at_utc, level, event, details_json) VALUES(?, ?, ?, ?)",
            (utcnow_iso(), level, event, json.dumps(details or {}, separators=(",", ":"))),
        )

    def save_account_snapshot(self, *, payload: dict) -> None:
        self._conn.execute(
            "INSERT INTO account_snapshots(created_at_utc, payload_json) VALUES(?, ?)",
            (utcnow_iso(), json.dumps(payload, separators=(",", ":"))),
        )

    def upsert_balances(self, balances: Iterable[Balance]) -> None:
        now = utcnow_iso()
        self._conn.executemany(
            """
            INSERT INTO balances(asset, free, locked, snapshot_time_utc, updated_at_utc)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(asset) DO UPDATE SET
              free = excluded.free,
              locked = excluded.locked,
              snapshot_time_utc = excluded.snapshot_time_utc,
              updated_at_utc = excluded.updated_at_utc
            """,
            [(b.asset, b.free, b.locked, now, now) for b in balances],
        )

    def upsert_orders(self, orders: Iterable[OrderRow]) -> None:
        orders_list = list(orders)
        if not orders_list:
            return
        self._conn.executemany(
            """
            INSERT INTO orders(
              exchange_order_id, symbol, side, type, status, time_in_force,
              price, quantity, filled_quantity, executed_quantity,
              created_at_utc, updated_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(exchange_order_id) DO UPDATE SET
              symbol = excluded.symbol,
              side = excluded.side,
              type = excluded.type,
              status = excluded.status,
              time_in_force = excluded.time_in_force,
              price = excluded.price,
              quantity = excluded.quantity,
              filled_quantity = excluded.filled_quantity,
              executed_quantity = excluded.executed_quantity,
              updated_at_utc = excluded.updated_at_utc
            """,
            [
                (
                    o.exchange_order_id,
                    o.symbol,
                    o.side,
                    o.type,
                    o.status,
                    o.time_in_force,
                    o.price,
                    o.quantity,
                    o.filled_quantity,
                    o.executed_quantity,
                    o.created_at_utc,
                    o.updated_at_utc,
                )
                for o in orders_list
                if o.exchange_order_id is not None
            ],
        )

    def sync_open_orders(self, open_orders: Iterable[OrderRow], *, symbol: str | None = None) -> None:
        """
        Exchange is source of truth.
        Mark previously open orders as CLOSED, then upsert currently open ones.
        """
        now = utcnow_iso()
        if symbol:
            self._conn.execute(
                "UPDATE orders SET status = ?, updated_at_utc = ? WHERE symbol = ? AND status IN ('NEW','PARTIALLY_FILLED')",
                ("CLOSED", now, symbol),
            )
        else:
            self._conn.execute(
                "UPDATE orders SET status = ?, updated_at_utc = ? WHERE status IN ('NEW','PARTIALLY_FILLED')",
                ("CLOSED", now),
            )
        self.upsert_orders(open_orders)

    def get_last_sync(self) -> dict | None:
        cur = self._conn.execute(
            "SELECT kind, started_at_utc, finished_at_utc, status, error_msg FROM sync_runs ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_balance_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) AS n FROM balances")
        return int(cur.fetchone()["n"])

    def get_open_order_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status IN ('NEW','PARTIALLY_FILLED')")
        return int(cur.fetchone()["n"])

    def create_trade_request(self, req: ValidatedTradeRequest) -> int:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            INSERT INTO trade_requests(
              request_id, status, preferred_symbol, exit_asset, label, notes,
              budget_mode, budget_asset, budget_amount,
              profit_target_pct, stop_loss_pct, deadline_hours, deadline_utc,
              created_at_utc, updated_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                "DRAFT",
                req.preferred_symbol,
                req.exit_asset,
                req.label,
                req.notes,
                req.budget_mode,
                req.budget_asset,
                str(req.budget_amount) if req.budget_amount is not None else None,
                str(req.profit_target_pct),
                str(req.stop_loss_pct),
                req.deadline_hours,
                req.deadline_utc.replace(microsecond=0).isoformat(),
                now,
                now,
            ),
        )
        row_id = int(cur.lastrowid)
        # Generate a stable request_id for display/auditing.
        request_id = f"tr_{row_id:06d}"
        self._conn.execute("UPDATE trade_requests SET request_id = ?, updated_at_utc = ? WHERE id = ?", (request_id, now, row_id))
        return row_id

    def list_trade_requests(self, *, limit: int | None = None) -> list[dict]:
        sql = (
            "SELECT id, request_id, status, preferred_symbol, budget_mode, budget_asset, budget_amount, "
            "profit_target_pct, stop_loss_pct, deadline_utc, validation_status, created_at_utc, updated_at_utc "
            "FROM trade_requests ORDER BY id DESC"
        )
        params: list[object] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def get_trade_request(self, trade_request_id: int) -> dict | None:
        cur = self._conn.execute(
            "SELECT * FROM trade_requests WHERE id = ?",
            (int(trade_request_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def cancel_trade_request(self, trade_request_id: int) -> bool:
        now = utcnow_iso()
        cur = self._conn.execute(
            "UPDATE trade_requests SET status = ?, updated_at_utc = ? WHERE id = ? AND status IN ('NEW','DRAFT','VALIDATED')",
            ("CANCELLED", now, int(trade_request_id)),
        )
        return int(cur.rowcount) > 0

    def set_trade_request_validation(
        self,
        *,
        trade_request_id: int,
        validation_status: str,
        validation_error: str | None,
        last_price: str | None,
        estimated_qty: str | None,
        symbol_base_asset: str | None,
        symbol_quote_asset: str | None,
    ) -> bool:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            UPDATE trade_requests
            SET validation_status = ?,
                validation_error = ?,
                validated_at_utc = ?,
                last_price = ?,
                estimated_qty = ?,
                symbol_base_asset = ?,
                symbol_quote_asset = ?,
                updated_at_utc = ?
            WHERE id = ? AND status IN ('NEW','DRAFT','VALIDATED')
            """,
            (
                validation_status,
                validation_error,
                now,
                last_price,
                estimated_qty,
                symbol_base_asset,
                symbol_quote_asset,
                now,
                int(trade_request_id),
            ),
        )
        return int(cur.rowcount) > 0

    def list_balances(self, *, include_zero: bool, limit: int | None = None) -> list[dict]:
        cur = self._conn.execute("SELECT asset, free, locked, updated_at_utc FROM balances ORDER BY asset ASC")
        rows = [dict(r) for r in cur.fetchall()]
        if include_zero:
            return rows[:limit] if limit is not None else rows

        def _is_zero(s: object) -> bool:
            try:
                return Decimal(str(s)) == 0
            except (InvalidOperation, ValueError):
                return False

        filtered = [r for r in rows if not (_is_zero(r.get("free")) and _is_zero(r.get("locked")))]
        return filtered[:limit] if limit is not None else filtered

    def list_open_orders(self, *, symbol: str | None = None, limit: int | None = None) -> list[dict]:
        sql = (
            "SELECT exchange_order_id, symbol, side, type, status, price, quantity, filled_quantity, "
            "created_at_utc, updated_at_utc "
            "FROM orders WHERE status IN ('NEW','PARTIALLY_FILLED')"
        )
        params: list[object] = []
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        sql += " ORDER BY updated_at_utc DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def get_cached_balance_free(self, *, asset: str) -> Decimal | None:
        cur = self._conn.execute("SELECT free FROM balances WHERE asset = ?", (asset.strip().upper(),))
        row = cur.fetchone()
        if not row:
            return None
        try:
            return Decimal(str(row["free"]))
        except (InvalidOperation, ValueError):
            return None

    def create_trade_plan(
        self,
        *,
        trade_request_id: int,
        request_id: str | None,
        status: str,
        feasibility_category: str,
        warnings_json: str | None,
        rejection_reason: str | None,
        market_data_environment: str,
        execution_environment: str,
        symbol: str,
        price: str,
        bid: str | None,
        ask: str | None,
        spread_pct: str | None,
        volume_24h_quote: str | None,
        volatility_pct: str | None,
        momentum_pct: str | None,
        budget_mode: str,
        approved_budget_asset: str,
        approved_budget_amount: str | None,
        usable_budget_amount: str | None,
        raw_quantity: str | None,
        rounded_quantity: str | None,
        expected_notional: str | None,
        rules_snapshot_json: str,
        market_summary_json: str,
        candidate_list_json: str | None,
        signal: str,
        signal_reasons_json: str | None,
        created_at_utc: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO trade_plans(
              trade_request_id, request_id, status, feasibility_category, warnings_json, rejection_reason,
              market_data_environment, execution_environment,
              symbol, price, bid, ask, spread_pct,
              volume_24h_quote, volatility_pct, momentum_pct,
              budget_mode, approved_budget_asset, approved_budget_amount, usable_budget_amount,
              raw_quantity, rounded_quantity, expected_notional,
              rules_snapshot_json, market_summary_json, candidate_list_json,
              signal, signal_reasons_json, created_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(trade_request_id),
                request_id,
                status,
                feasibility_category,
                warnings_json,
                rejection_reason,
                market_data_environment,
                execution_environment,
                symbol,
                price,
                bid,
                ask,
                spread_pct,
                volume_24h_quote,
                volatility_pct,
                momentum_pct,
                budget_mode,
                approved_budget_asset,
                approved_budget_amount,
                usable_budget_amount,
                raw_quantity,
                rounded_quantity,
                expected_notional,
                rules_snapshot_json,
                market_summary_json,
                candidate_list_json,
                signal,
                signal_reasons_json,
                created_at_utc,
            ),
        )
        return int(cur.lastrowid)

    def list_trade_plans(self, *, limit: int = 20) -> list[dict]:
        cur = self._conn.execute(
            """
            SELECT
              id,
              trade_request_id,
              request_id,
              symbol,
              feasibility_category,
              approved_budget_asset,
              approved_budget_amount,
              status,
              warnings_json,
              created_at_utc
            FROM trade_plans
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_trade_plan(self, *, plan_id: int) -> dict | None:
        cur = self._conn.execute("SELECT * FROM trade_plans WHERE id = ?", (int(plan_id),))
        row = cur.fetchone()
        return dict(row) if row else None

    def create_execution_candidate(
        self,
        *,
        trade_plan_id: int,
        trade_request_id: int,
        request_id: str | None,
        symbol: str,
        side: str,
        order_type: str,
        limit_price: str | None,
        execution_environment: str,
        validation_status: str,
        risk_status: str,
        approved_budget_asset: str,
        approved_budget_amount: str,
        approved_quantity: str,
        execution_ready: bool,
        summary: str,
        details_json: str | None,
    ) -> int:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            INSERT INTO execution_candidates(
              trade_plan_id, trade_request_id, request_id,
              symbol, side, order_type, limit_price, execution_environment,
              validation_status, risk_status,
              approved_budget_asset, approved_budget_amount, approved_quantity,
              execution_ready, summary, details_json,
              created_at_utc, updated_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(trade_plan_id),
                int(trade_request_id),
                request_id,
                symbol,
                side,
                order_type,
                limit_price,
                execution_environment,
                validation_status,
                risk_status,
                approved_budget_asset,
                approved_budget_amount,
                approved_quantity,
                1 if execution_ready else 0,
                summary,
                details_json,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)

    def get_execution_candidate(self, *, candidate_id: int) -> dict | None:
        cur = self._conn.execute("SELECT * FROM execution_candidates WHERE id = ?", (int(candidate_id),))
        row = cur.fetchone()
        return dict(row) if row else None

    def create_execution(
        self,
        *,
        candidate_id: int,
        plan_id: int,
        trade_request_id: int,
        symbol: str,
        side: str,
        order_type: str,
        execution_environment: str,
        client_order_id: str,
        quote_order_qty: str | None,
        limit_price: str | None = None,
        time_in_force: str | None = None,
        requested_quantity: str | None = None,
    ) -> int:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            INSERT INTO executions(
              candidate_id, plan_id, trade_request_id,
              symbol, side, order_type, execution_environment,
              client_order_id, binance_order_id,
              quote_order_qty, limit_price, time_in_force, requested_quantity,
              executed_quantity, avg_fill_price, total_quote_spent,
              commission_total, commission_asset, fills_count,
              local_status, raw_status, retry_count,
              submitted_at_utc, reconciled_at_utc,
              expired_at_utc, created_at_utc, updated_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(candidate_id),
                int(plan_id),
                int(trade_request_id),
                symbol,
                side,
                order_type,
                execution_environment,
                client_order_id,
                None,
                quote_order_qty,
                limit_price,
                time_in_force,
                requested_quantity,
                None,
                None,
                None,
                None,
                None,
                None,
                "submitting",
                None,
                0,
                None,
                None,
                None,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)

    def update_execution(
        self,
        *,
        execution_id: int,
        local_status: str,
        raw_status: str | None,
        binance_order_id: str | None,
        executed_quantity: str | None,
        avg_fill_price: str | None,
        total_quote_spent: str | None,
        commission_total: str | None,
        commission_asset: str | None,
        fills_count: int | None,
        retry_count: int,
        message: str,
        details_json: str | None,
        submitted_at_utc: str | None,
        reconciled_at_utc: str | None,
        expired_at_utc: str | None = None,
    ) -> None:
        now = utcnow_iso()
        self._conn.execute(
            """
            UPDATE executions
            SET local_status = ?,
                raw_status = ?,
                binance_order_id = ?,
                executed_quantity = ?,
                avg_fill_price = ?,
                total_quote_spent = ?,
                commission_total = ?,
                commission_asset = ?,
                fills_count = ?,
                retry_count = ?,
                submitted_at_utc = COALESCE(submitted_at_utc, ?),
                reconciled_at_utc = ?,
                expired_at_utc = COALESCE(expired_at_utc, ?),
                updated_at_utc = ?
            WHERE execution_id = ?
            """,
            (
                local_status,
                raw_status,
                binance_order_id,
                executed_quantity,
                avg_fill_price,
                total_quote_spent,
                commission_total,
                commission_asset,
                fills_count,
                int(retry_count),
                submitted_at_utc,
                reconciled_at_utc,
                expired_at_utc,
                now,
                int(execution_id),
            ),
        )
        # Store human-readable message/details in audit log (executions table stays normalized).
        self.append_audit(
            level="INFO" if local_status in ("filled", "submitted", "partially_filled") else "WARN",
            event="execution_update",
            details={
                "execution_id": int(execution_id),
                "local_status": local_status,
                "message": message,
                "details": details_json,
            },
        )

    def mark_execution_expired(self, *, execution_id: int, reason: str) -> None:
        now = utcnow_iso()
        self._conn.execute(
            """
            UPDATE executions
            SET local_status = 'expired',
                expired_at_utc = COALESCE(expired_at_utc, ?),
                reconciled_at_utc = ?,
                updated_at_utc = ?
            WHERE execution_id = ?
            """,
            (now, now, now, int(execution_id)),
        )
        self.append_audit(level="WARN", event="execution_expired", details={"execution_id": int(execution_id), "reason": reason})

    def list_executions(self, *, limit: int = 20) -> list[dict]:
        cur = self._conn.execute(
            """
            SELECT
              execution_id,
              candidate_id,
              plan_id,
              trade_request_id,
              symbol,
              side,
              order_type,
              execution_environment,
              client_order_id,
              binance_order_id,
              quote_order_qty,
              limit_price,
              time_in_force,
              executed_quantity,
              avg_fill_price,
              total_quote_spent,
              commission_total,
              commission_asset,
              fills_count,
              local_status,
              raw_status,
              retry_count,
              submitted_at_utc,
              reconciled_at_utc,
              expired_at_utc,
              created_at_utc,
              updated_at_utc
            FROM executions
            ORDER BY execution_id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_execution(self, *, execution_id: int) -> dict | None:
        cur = self._conn.execute("SELECT * FROM executions WHERE execution_id = ?", (int(execution_id),))
        row = cur.fetchone()
        return dict(row) if row else None

    def has_nonterminal_execution_for_candidate(self, *, candidate_id: int) -> bool:
        """
        Returns True if this candidate already has an execution attempt that is not terminal.
        This prevents accidental duplicate executions from the same approved candidate.
        """
        cur = self._conn.execute(
            """
            SELECT 1
            FROM executions
            WHERE candidate_id = ?
              AND local_status IN ('submitting','submitted','uncertain_submitted','filled','partially_filled')
            LIMIT 1
            """,
            (int(candidate_id),),
        )
        return cur.fetchone() is not None

    def list_reconcilable_executions(self, *, limit: int = 50) -> list[dict]:
        cur = self._conn.execute(
            """
            SELECT
              execution_id,
              candidate_id,
              plan_id,
              trade_request_id,
              symbol,
              order_type,
              execution_environment,
              client_order_id,
              local_status,
              raw_status,
              retry_count,
              submitted_at_utc,
              limit_price,
              time_in_force
            FROM executions
            WHERE local_status IN ('uncertain_submitted','submitted','open','partially_filled')
            ORDER BY execution_id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(r) for r in cur.fetchall()]

    def create_position(
        self,
        *,
        symbol: str,
        entry_price: str,
        quantity: str,
        stop_loss_price: str,
        profit_target_price: str,
        deadline_utc: str,
    ) -> int:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            INSERT INTO positions(
              symbol, entry_price, quantity, stop_loss_price, profit_target_price, deadline_utc,
              status, opened_at_utc, created_at_utc, updated_at_utc
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                entry_price,
                quantity,
                stop_loss_price,
                profit_target_price,
                deadline_utc,
                "OPEN",
                now,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)

    def get_active_position(self, *, symbol: str | None = None) -> dict | None:
        if symbol:
            cur = self._conn.execute(
                "SELECT * FROM positions WHERE status = 'OPEN' AND symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            )
        else:
            cur = self._conn.execute("SELECT * FROM positions WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None

    def close_position(self, *, position_id: int, status: str = "CLOSED") -> bool:
        now = utcnow_iso()
        cur = self._conn.execute(
            """
            UPDATE positions
            SET status = ?, closed_at_utc = ?, updated_at_utc = ?
            WHERE id = ? AND status = 'OPEN'
            """,
            (status, now, now, int(position_id)),
        )
        return int(cur.rowcount) > 0

    def list_audit_logs(self, *, limit: int = 50) -> list[dict]:
        cur = self._conn.execute(
            "SELECT created_at_utc, level, event, details_json FROM audit_logs ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        return [dict(r) for r in cur.fetchall()]
