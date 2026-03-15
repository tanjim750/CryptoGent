PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_start_time_utc TEXT,
  last_shutdown_time_utc TEXT,
  last_successful_sync_time_utc TEXT,
  current_mode TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at_utc TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS balances (
  asset TEXT PRIMARY KEY,
  free TEXT NOT NULL,
  locked TEXT NOT NULL,
  snapshot_time_utc TEXT,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exchange_order_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  time_in_force TEXT,
  price TEXT,
  quantity TEXT NOT NULL,
  filled_quantity TEXT NOT NULL,
  executed_quantity TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_exchange_order_id ON orders(exchange_order_id);

CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  started_at_utc TEXT NOT NULL,
  finished_at_utc TEXT,
  status TEXT NOT NULL,
  error_msg TEXT
);

CREATE TABLE IF NOT EXISTS trade_requests (
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
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  entry_price TEXT NOT NULL,
  quantity TEXT NOT NULL,
  stop_loss_price TEXT NOT NULL,
  profit_target_price TEXT NOT NULL,
  deadline_utc TEXT NOT NULL,
  status TEXT NOT NULL,
  opened_at_utc TEXT,
  closed_at_utc TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

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
);

CREATE INDEX IF NOT EXISTS idx_trade_plans_trade_request_id ON trade_plans(trade_request_id);

CREATE TABLE IF NOT EXISTS execution_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trade_plan_id INTEGER NOT NULL,
  trade_request_id INTEGER NOT NULL,
  request_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  limit_price TEXT,
  execution_environment TEXT NOT NULL,
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
);

CREATE INDEX IF NOT EXISTS idx_execution_candidates_trade_plan_id ON execution_candidates(trade_plan_id);

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
  limit_price TEXT,
  time_in_force TEXT,
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
  expired_at_utc TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(candidate_id) REFERENCES execution_candidates(id),
  FOREIGN KEY(plan_id) REFERENCES trade_plans(id),
  FOREIGN KEY(trade_request_id) REFERENCES trade_requests(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_executions_client_order_id ON executions(client_order_id);
CREATE INDEX IF NOT EXISTS idx_executions_candidate_id ON executions(candidate_id);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at_utc TEXT NOT NULL,
  level TEXT NOT NULL,
  event TEXT NOT NULL,
  details_json TEXT
);
