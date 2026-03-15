# CryptoGent CLI Commands

Most commands accept:

- `--config <path>`: config TOML path (default: `./cryptogent.toml` or `$CRYPTOGENT_CONFIG`)
- `--db <path>`: SQLite DB path (default from config or `./cryptogent.sqlite3`)

## Setup

- `cryptogent init`  
  Create a default `cryptogent.toml` (if missing) and initialize the SQLite schema.

- `cryptogent menu`  
  Interactive menu wrapper over subcommands (includes creating + validating trade requests).

- `cryptogent status`  
  Show local paths plus cached-state counts (balances / open orders) and last sync status.

## Config

- `cryptogent config show`  
  Show effective config values (including whether testnet is enabled).

- `cryptogent config set-binance --api-key "…" --api-secret-stdin`  
  Store **mainnet** Binance API key/secret in `cryptogent.toml` (plaintext).

- `cryptogent config set-binance-testnet --api-key "…" --api-secret-stdin`  
  Store **testnet** Binance API key/secret in `cryptogent.toml` (plaintext, under `[binance_testnet]`).

- `cryptogent config use-testnet`  
  Toggle config to use Binance Spot Test Network (`binance.testnet = true`).

- `cryptogent config use-mainnet`  
  Toggle config back to real Binance Spot API (`binance.testnet = false`).

Notes:

- Recommended: use environment variables instead of storing secrets:
  - Mainnet: `BINANCE_API_KEY`, `BINANCE_API_SECRET`
  - Testnet: `BINANCE_TESTNET_API_KEY`, `BINANCE_TESTNET_API_SECRET`

## Exchange (no trading)

These are connectivity/read-only utilities. They support TLS/network flags:

- `--ca-bundle <pem>`: trust a custom CA bundle (for TLS-intercepting proxies)
- `--insecure`: disable TLS verification (debug only)
- `--testnet`: force Spot testnet for this command
- `--base-url <url>`: override base URL (escape hatch)

Commands:

- `cryptogent exchange ping`  
  Calls `GET /api/v3/ping` (quick connectivity check).

- `cryptogent exchange time`  
  Calls `GET /api/v3/time` (server timestamp in ms).

- `cryptogent exchange info [--symbol BTCUSDT]`  
  Calls `GET /api/v3/exchangeInfo` (optionally for a single symbol).

- `cryptogent exchange balances [--all]`  
  Calls `GET /api/v3/account` and prints balances (requires API key+secret).

## Sync (writes to SQLite; no trading)

Also supports: `--ca-bundle`, `--insecure`, `--testnet`, `--base-url`.

- `cryptogent sync startup`  
  Snapshot account + sync balances + sync open orders into SQLite.

- `cryptogent sync balances`  
  Sync balances into SQLite.

- `cryptogent sync open-orders [--symbol BTCUSDT]`  
  Sync open orders into SQLite (optionally filter by symbol).

## Show (reads from SQLite; no network)

- `cryptogent show balances [--all] [--limit N]`  
  Print cached balances from SQLite.

- `cryptogent show balances --filter USDT`  
  Filter cached balances by asset substring.

- `cryptogent show open-orders [--symbol BTCUSDT] [--limit N]`  
  Print cached open orders from SQLite.

- `cryptogent show audit [--limit N]`  
  Print recent audit log entries from SQLite (latest first).

## Trade (requests only; no execution)

- `cryptogent trade start --profit-target-pct 2.0 --deadline-hours 24 --budget-mode manual --budget 50 --budget-asset USDT --symbol BTCUSDT --exit-asset USDT`  
  Create a structured trade request in SQLite (no order placed). Prompts for confirmation unless `--yes` is provided.

- `cryptogent trade start --profit-target-pct 2.0 --deadline-hours 24 --budget-mode auto --budget-asset USDT --symbol BTCUSDT --exit-asset USDT --yes`  
  Create a request with auto budget selection (budget amount decided in later phases).

- `cryptogent trade list [--limit N]`  
  List stored trade requests (shows current validation status if present).

- `cryptogent trade show <id>`  
  Show one trade request (including last validation result).

- `cryptogent trade cancel <id>`  
  Cancel a `NEW` trade request.

- `cryptogent trade validate <id>`  
  Validates a trade request as a **gate**:
  - Rules/sizing check: Binance symbol rules (`exchangeInfo`) + current price (`ticker/price`)
  - Feasibility check: public market data (mainnet candles/stats/spread)
  Persists `VALID/INVALID/ERROR` + estimated quantity back into SQLite (no order placed).

- `cryptogent trade plan build <trade_request_id>`  
  Builds and persists a deterministic Phase 5 trade plan (public market data + rules snapshot + sizing; no order placed).

- `cryptogent trade plan list [--limit N]`  
  Lists stored trade plans.

- `cryptogent trade plan show <plan_id>`  
  Shows one stored trade plan (including rules snapshot and candidate list).

- `cryptogent trade safety <plan_id>`  
  Phase 6 safety validation (plan-based). Persists an `execution_candidates` row (no order placed).
  Use `--order-type LIMIT_BUY --limit-price <price>` to generate a LIMIT_BUY candidate.

Notes:
- Backwards-compatible alias: `cryptogent trade plan-build <trade_request_id>` (same as `trade plan build`).

## Execution (Phase 7)

- `cryptogent trade execute <candidate_id> [--yes]`  
  Phase 7 execution: submits a **BUY MARKET** using `quoteOrderQty = execution_candidates.approved_budget_amount`, with idempotent `newClientOrderId` + reconciliation on timeout. Persists an `executions` row.
  If the candidate has `order_type=LIMIT_BUY`, it submits a GTC LIMIT BUY using `price=limit_price` and a base `quantity` computed from the approved quote budget (tick/step/min-notional enforced from the stored rules snapshot).

- `cryptogent trade execution list [--limit N]`  
  List stored execution attempts.

- `cryptogent trade execution show <execution_id>`  
  Show one stored execution attempt.

- `cryptogent trade execution cancel <execution_id>`  
  Cancels an open LIMIT_BUY execution on Binance using the stored `client_order_id` (then reconciles locally).

- `cryptogent trade reconcile`  
  Reconcile in-flight/uncertain/open executions with Binance using `GET /api/v3/order` by `origClientOrderId`.
  Also marks open `LIMIT_BUY` executions as locally `expired` after `--limit-order-timeout-minutes` (default: 30). No auto-cancel by default.
  Use `--auto-cancel-expired` (or config `trading.auto_cancel_expired_limit_orders = true`) to also cancel the order on Binance when it times out.
