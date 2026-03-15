from __future__ import annotations

from pathlib import Path

from cryptogent.config.io import DEFAULT_DB_PATH, load_config
from cryptogent.db.connection import connect

TARGET_SCHEMA_VERSION = 12


def _read_schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")


def _get_schema_version(conn) -> int:
    try:
        cur = conn.execute("SELECT value FROM app_meta WHERE key = ?", ("schema_version",))
        row = cur.fetchone()
        return int(row["value"]) if row else 0
    except Exception:
        return 0


def _column_exists(conn, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in cur.fetchall())


def _column_notnull(conn, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    for r in cur.fetchall():
        if r["name"] == column:
            return bool(r["notnull"])
    return False


def _add_column_if_missing(conn, table: str, column: str, ddl_fragment: str) -> None:
    if _column_exists(conn, table, column):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl_fragment}")


def _migrate_to_v4(conn) -> None:
    _add_column_if_missing(conn, "trade_requests", "validation_status", "validation_status TEXT")
    _add_column_if_missing(conn, "trade_requests", "validation_error", "validation_error TEXT")
    _add_column_if_missing(conn, "trade_requests", "validated_at_utc", "validated_at_utc TEXT")
    _add_column_if_missing(conn, "trade_requests", "last_price", "last_price TEXT")
    _add_column_if_missing(conn, "trade_requests", "estimated_qty", "estimated_qty TEXT")
    _add_column_if_missing(conn, "trade_requests", "symbol_base_asset", "symbol_base_asset TEXT")
    _add_column_if_missing(conn, "trade_requests", "symbol_quote_asset", "symbol_quote_asset TEXT")


def _migrate_to_v5(conn) -> None:
    # Phase 3 Local State refinements
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS system_state (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          last_start_time_utc TEXT,
          last_shutdown_time_utc TEXT,
          last_successful_sync_time_utc TEXT,
          current_mode TEXT,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL
        )
        """
    )

    _add_column_if_missing(conn, "balances", "snapshot_time_utc", "snapshot_time_utc TEXT")

    _add_column_if_missing(conn, "orders", "time_in_force", "time_in_force TEXT")
    _add_column_if_missing(conn, "orders", "executed_quantity", "executed_quantity TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_exchange_order_id ON orders(exchange_order_id)")

    _add_column_if_missing(conn, "positions", "opened_at_utc", "opened_at_utc TEXT")
    _add_column_if_missing(conn, "positions", "closed_at_utc", "closed_at_utc TEXT")


def _migrate_to_v6(conn) -> None:
    # Phase 4 Trade Input refinements
    # If an older DB has budget_amount as NOT NULL, we rebuild the table to allow NULL (needed for budget_mode=auto).
    if _column_exists(conn, "trade_requests", "budget_amount") and _column_notnull(conn, "trade_requests", "budget_amount"):
        conn.execute(
            """
            CREATE TABLE trade_requests_new (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              request_id TEXT,
              status TEXT NOT NULL,
              preferred_symbol TEXT,
              exit_asset TEXT,
              label TEXT,
              notes TEXT,
              budget_mode TEXT NOT NULL,
              budget_asset TEXT NOT NULL,
              budget_amount TEXT,
              profit_target_pct TEXT NOT NULL,
              stop_loss_pct TEXT NOT NULL,
              deadline_hours INTEGER,
              deadline_utc TEXT NOT NULL,
              validation_status TEXT,
              validation_error TEXT,
              validated_at_utc TEXT,
              last_price TEXT,
              estimated_qty TEXT,
              symbol_base_asset TEXT,
              symbol_quote_asset TEXT,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO trade_requests_new(
              id, request_id, status, preferred_symbol, exit_asset, label, notes,
              budget_mode, budget_asset, budget_amount,
              profit_target_pct, stop_loss_pct, deadline_hours, deadline_utc,
              validation_status, validation_error, validated_at_utc, last_price, estimated_qty,
              symbol_base_asset, symbol_quote_asset,
              created_at_utc, updated_at_utc
            )
            SELECT
              id,
              NULL,
              status,
              preferred_symbol,
              NULL,
              NULL,
              NULL,
              COALESCE(budget_mode, 'manual'),
              budget_asset,
              budget_amount,
              profit_target_pct,
              stop_loss_pct,
              NULL,
              deadline_utc,
              validation_status,
              validation_error,
              validated_at_utc,
              last_price,
              estimated_qty,
              symbol_base_asset,
              symbol_quote_asset,
              created_at_utc,
              updated_at_utc
            FROM trade_requests
            """
        )
        conn.execute("DROP TABLE trade_requests")
        conn.execute("ALTER TABLE trade_requests_new RENAME TO trade_requests")

    _add_column_if_missing(conn, "trade_requests", "request_id", "request_id TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_requests_request_id ON trade_requests(request_id)")

    _add_column_if_missing(conn, "trade_requests", "exit_asset", "exit_asset TEXT")
    _add_column_if_missing(conn, "trade_requests", "label", "label TEXT")
    _add_column_if_missing(conn, "trade_requests", "notes", "notes TEXT")
    _add_column_if_missing(conn, "trade_requests", "budget_mode", "budget_mode TEXT")
    _add_column_if_missing(conn, "trade_requests", "deadline_hours", "deadline_hours INTEGER")


def _migrate_to_v7(conn) -> None:
    # Repair migration: ensure trade_requests.budget_amount can be NULL (needed for budget_mode=auto).
    if _column_exists(conn, "trade_requests", "budget_amount") and _column_notnull(conn, "trade_requests", "budget_amount"):
        conn.execute(
            """
            CREATE TABLE trade_requests_new (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              request_id TEXT,
              status TEXT NOT NULL,
              preferred_symbol TEXT,
              exit_asset TEXT,
              label TEXT,
              notes TEXT,
              budget_mode TEXT NOT NULL,
              budget_asset TEXT NOT NULL,
              budget_amount TEXT,
              profit_target_pct TEXT NOT NULL,
              stop_loss_pct TEXT NOT NULL,
              deadline_hours INTEGER,
              deadline_utc TEXT NOT NULL,
              validation_status TEXT,
              validation_error TEXT,
              validated_at_utc TEXT,
              last_price TEXT,
              estimated_qty TEXT,
              symbol_base_asset TEXT,
              symbol_quote_asset TEXT,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO trade_requests_new(
              id, request_id, status, preferred_symbol, exit_asset, label, notes,
              budget_mode, budget_asset, budget_amount,
              profit_target_pct, stop_loss_pct, deadline_hours, deadline_utc,
              validation_status, validation_error, validated_at_utc, last_price, estimated_qty,
              symbol_base_asset, symbol_quote_asset,
              created_at_utc, updated_at_utc
            )
            SELECT
              id,
              request_id,
              status,
              preferred_symbol,
              exit_asset,
              label,
              notes,
              COALESCE(budget_mode, 'manual'),
              budget_asset,
              budget_amount,
              profit_target_pct,
              stop_loss_pct,
              deadline_hours,
              deadline_utc,
              validation_status,
              validation_error,
              validated_at_utc,
              last_price,
              estimated_qty,
              symbol_base_asset,
              symbol_quote_asset,
              created_at_utc,
              updated_at_utc
            FROM trade_requests
            """
        )
        conn.execute("DROP TABLE trade_requests")
        conn.execute("ALTER TABLE trade_requests_new RENAME TO trade_requests")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_requests_request_id ON trade_requests(request_id)")


def _migrate_to_v8(conn) -> None:
    # Phase 5 Market and Planning: trade_plans table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trade_plans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          trade_request_id INTEGER NOT NULL,
          request_id TEXT,
          status TEXT NOT NULL,
          feasibility_category TEXT NOT NULL,
          warnings_json TEXT,
          rejection_reason TEXT,
          market_data_environment TEXT NOT NULL,
          execution_environment TEXT NOT NULL,
          symbol TEXT NOT NULL,
          price TEXT NOT NULL,
          bid TEXT,
          ask TEXT,
          spread_pct TEXT,
          volume_24h_quote TEXT,
          volatility_pct TEXT,
          momentum_pct TEXT,
          budget_mode TEXT NOT NULL,
          approved_budget_asset TEXT NOT NULL,
          approved_budget_amount TEXT,
          usable_budget_amount TEXT,
          raw_quantity TEXT,
          rounded_quantity TEXT,
          expected_notional TEXT,
          rules_snapshot_json TEXT NOT NULL,
          market_summary_json TEXT NOT NULL,
          candidate_list_json TEXT,
          signal TEXT NOT NULL,
          signal_reasons_json TEXT,
          created_at_utc TEXT NOT NULL,
          FOREIGN KEY(trade_request_id) REFERENCES trade_requests(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_plans_trade_request_id ON trade_plans(trade_request_id)")


def _migrate_to_v9(conn) -> None:
    # Phase 6 Safety: execution candidates table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_candidates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          trade_plan_id INTEGER NOT NULL,
          trade_request_id INTEGER NOT NULL,
          request_id TEXT,
          symbol TEXT NOT NULL,
          side TEXT NOT NULL,
          validation_status TEXT NOT NULL,
          risk_status TEXT NOT NULL,
          approved_budget_asset TEXT NOT NULL,
          approved_budget_amount TEXT NOT NULL,
          approved_quantity TEXT NOT NULL,
          execution_ready INTEGER NOT NULL,
          summary TEXT NOT NULL,
          details_json TEXT,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL,
          FOREIGN KEY(trade_plan_id) REFERENCES trade_plans(id),
          FOREIGN KEY(trade_request_id) REFERENCES trade_requests(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_execution_candidates_trade_plan_id ON execution_candidates(trade_plan_id)"
    )


def _migrate_to_v10(conn) -> None:
    # Phase 7 Execution: executions table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS executions (
          execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
          candidate_id INTEGER NOT NULL,
          plan_id INTEGER NOT NULL,
          trade_request_id INTEGER NOT NULL,
          symbol TEXT NOT NULL,
          side TEXT NOT NULL,
          order_type TEXT NOT NULL,
          execution_environment TEXT NOT NULL,
          client_order_id TEXT NOT NULL,
          binance_order_id TEXT,
          quote_order_qty TEXT,
          requested_quantity TEXT,
          executed_quantity TEXT,
          avg_fill_price TEXT,
          total_quote_spent TEXT,
          commission_total TEXT,
          commission_asset TEXT,
          fills_count INTEGER,
          local_status TEXT NOT NULL,
          raw_status TEXT,
          retry_count INTEGER NOT NULL,
          submitted_at_utc TEXT,
          reconciled_at_utc TEXT,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL,
          FOREIGN KEY(candidate_id) REFERENCES execution_candidates(id),
          FOREIGN KEY(plan_id) REFERENCES trade_plans(id),
          FOREIGN KEY(trade_request_id) REFERENCES trade_requests(id)
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_executions_client_order_id ON executions(client_order_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_candidate_id ON executions(candidate_id)")


def _migrate_to_v11(conn) -> None:
    # Phase 7 LIMIT BUY extension: add candidate + execution fields
    _add_column_if_missing(conn, "execution_candidates", "order_type", "order_type TEXT NOT NULL DEFAULT 'MARKET_BUY'")
    _add_column_if_missing(conn, "execution_candidates", "limit_price", "limit_price TEXT")

    _add_column_if_missing(conn, "executions", "limit_price", "limit_price TEXT")
    _add_column_if_missing(conn, "executions", "time_in_force", "time_in_force TEXT")
    _add_column_if_missing(conn, "executions", "expired_at_utc", "expired_at_utc TEXT")


def _migrate_to_v12(conn) -> None:
    # Phase 7 LIMIT BUY lock-ins: execution_candidates must store execution_environment.
    _add_column_if_missing(
        conn,
        "execution_candidates",
        "execution_environment",
        "execution_environment TEXT NOT NULL DEFAULT 'mainnet'",
    )
    # Best-effort backfill from linked plan.
    try:
        conn.execute(
            """
            UPDATE execution_candidates
            SET execution_environment = (
              SELECT execution_environment FROM trade_plans WHERE trade_plans.id = execution_candidates.trade_plan_id
            )
            WHERE execution_environment IS NULL OR execution_environment = ''
            """
        )
    except Exception:
        pass


def ensure_db_initialized(*, config_path: Path, db_path: Path | None) -> Path:
    cfg = load_config(config_path)
    resolved_db_path = (db_path or cfg.db_path or DEFAULT_DB_PATH).expanduser()

    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = _read_schema_sql()

    with connect(resolved_db_path) as conn:
        conn.executescript(schema_sql)
        current = _get_schema_version(conn)
        if current < 4:
            _migrate_to_v4(conn)
        if current < 5:
            _migrate_to_v5(conn)
        if current < 6:
            _migrate_to_v6(conn)
        if current < 7:
            _migrate_to_v7(conn)
        if current < 8:
            _migrate_to_v8(conn)
        if current < 9:
            _migrate_to_v9(conn)
        if current < 10:
            _migrate_to_v10(conn)
        if current < 11:
            _migrate_to_v11(conn)
        if current < 12:
            _migrate_to_v12(conn)
        conn.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES(?, ?)",
            ("schema_version", str(TARGET_SCHEMA_VERSION)),
        )

    return resolved_db_path
