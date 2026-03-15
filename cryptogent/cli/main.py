from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path
from datetime import UTC, datetime

from cryptogent.config.io import BINANCE_SPOT_BASE_URL, ConfigPaths, ensure_default_config
from cryptogent.config.io import load_config
from cryptogent.config.edit import BinanceCredentialUpdate, update_binance_config
from cryptogent.db.migrate import ensure_db_initialized
from cryptogent.db.connection import connect
from cryptogent.exchange.binance_errors import BinanceAPIError
from cryptogent.exchange.binance_spot import BinanceSpotClient
from cryptogent.market.market_data_service import MarketDataError, fetch_market_snapshot
from cryptogent.planning.trade_planner import PlanningError, build_trade_plan, persist_trade_plan
from cryptogent.safety.validator import SafetyError, evaluate_safety
from cryptogent.execution.executor import ExecutionError, execute_limit_buy, execute_market_buy_quote
from cryptogent.state.manager import StateManager
from cryptogent.sync.binance_sync import startup_sync, sync_balances, sync_open_orders
from cryptogent.validation.trade_request import ValidationError, validate_trade_request
from cryptogent.validation.binance_rules import parse_symbol_rules, precheck_market_buy, RuleError
from cryptogent.planning.feasibility import FeasibilityError, evaluate_feasibility, freshness_and_consistency_checks
from cryptogent.util.time import utcnow_iso
from decimal import Decimal, InvalidOperation


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config TOML (default: ./cryptogent.toml or $CRYPTOGENT_CONFIG).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite DB (default from config or ./cryptogent.sqlite3).",
    )

def _add_exchange_tls_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ca-bundle",
        type=Path,
        default=None,
        help="Path to a PEM CA bundle to trust (useful behind TLS-intercepting proxies).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS cert verification (debug only; not recommended).",
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        help='Use Binance Spot Test Network (base URL "https://testnet.binance.vision").',
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help='Override Binance base URL (e.g. "https://api.binance.com").',
    )


def cmd_init(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    print(f"Config: {config_path}")
    print(f"DB:     {db_path}")
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    print(f"Config: {config_path}")
    print(f"- db_path: {cfg.db_path}")
    print(f"- binance_base_url: {cfg.binance_base_url}")
    print(f"- binance_testnet: {cfg.binance_testnet}")
    print(f"- binance_timeout_s: {cfg.binance_timeout_s}")
    print(f"- binance_recv_window_ms: {cfg.binance_recv_window_ms}")
    print(f"- binance_tls_verify: {cfg.binance_tls_verify}")
    print(f"- binance_ca_bundle_path: {cfg.binance_ca_bundle_path}")
    print(f"- binance_api_key_set: {bool(cfg.binance_api_key)}")
    print(f"- binance_api_secret_set: {bool(cfg.binance_api_secret)}")
    print(f"- trading_auto_cancel_expired_limit_orders: {cfg.trading_auto_cancel_expired_limit_orders}")
    return 0


def cmd_config_set_binance(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)

    api_secret = args.api_secret
    if args.api_secret_stdin:
        api_secret = sys.stdin.read().strip()

    if args.testnet or args.base_url:
        print("Use `cryptogent config use-testnet` / `cryptogent config use-mainnet` to toggle networks.")
        return 2

    if not args.api_key and api_secret is None:
        print("Nothing to update (provide --api-key and/or --api-secret/--api-secret-stdin).")
        return 2

    update_binance_config(
        config_path,
        BinanceCredentialUpdate(
            api_key=args.api_key if args.api_key else None,
            api_secret=api_secret if api_secret not in (None, "") else None,
        ),
    )
    print(f"Updated: {config_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        state.ensure_system_state()
        mode = "TESTNET" if load_config(config_path).binance_testnet else "MAINNET"
        state.update_system_start(current_mode=mode)
        last_sync = state.get_last_sync()
        bal_n = state.get_balance_count()
        oo_n = state.get_open_order_count()
        system_state = state.get_system_state()
    print("CryptoGent status:")
    print(f"- config: {config_path}")
    print(f"- db:     {db_path}")
    print(f"- mode:   {mode}")
    print(f"- cached balances: {bal_n}")
    print(f"- cached open orders: {oo_n}")
    if last_sync:
        print(f"- last sync: {last_sync.get('kind')} {last_sync.get('status')} finished={last_sync.get('finished_at_utc')}")
    if system_state:
        print(f"- last start: {system_state.get('last_start_time_utc')}")
        print(f"- last shutdown: {system_state.get('last_shutdown_time_utc')}")
        print(f"- last successful sync: {system_state.get('last_successful_sync_time_utc')}")
    return 0


def _client_from_args(args: argparse.Namespace) -> BinanceSpotClient:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    client = BinanceSpotClient.from_config(cfg)

    # Base URL overrides (CLI wins).
    # `--testnet` forces testnet regardless of config.
    if getattr(args, "testnet", False):
        client = BinanceSpotClient(**{**client.__dict__, "base_url": "https://testnet.binance.vision"})
        tkey = os.environ.get("BINANCE_TESTNET_API_KEY")
        tsecret = os.environ.get("BINANCE_TESTNET_API_SECRET")
        if tkey:
            client = BinanceSpotClient(**{**client.__dict__, "api_key": tkey})
        if tsecret:
            client = BinanceSpotClient(**{**client.__dict__, "api_secret": tsecret})
    # `--base-url` remains as an escape hatch.
    if getattr(args, "base_url", None):
        client = BinanceSpotClient(**{**client.__dict__, "base_url": str(args.base_url).strip()})

    if getattr(args, "ca_bundle", None):
        client = BinanceSpotClient(
            **{**client.__dict__, "ca_bundle_path": args.ca_bundle.expanduser(), "tls_verify": True}
        )
    if getattr(args, "insecure", False):
        client = BinanceSpotClient(**{**client.__dict__, "tls_verify": False})

    # If config selected testnet, loader already switched keys; but allow env to override either way.
    return client


def cmd_config_use_testnet(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    update_binance_config(config_path, BinanceCredentialUpdate(testnet=True))
    print(f"Updated: {config_path} (binance.testnet = true)")
    return 0


def cmd_config_use_mainnet(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    update_binance_config(config_path, BinanceCredentialUpdate(testnet=False))
    print(f"Updated: {config_path} (binance.testnet = false)")
    return 0


def cmd_config_set_binance_testnet(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)

    api_secret = args.api_secret
    if args.api_secret_stdin:
        api_secret = sys.stdin.read().strip()

    if not args.api_key and api_secret is None:
        print("Nothing to update (provide --api-key and/or --api-secret/--api-secret-stdin).")
        return 2

    update_binance_config(
        config_path,
        BinanceCredentialUpdate(
            testnet_api_key=args.api_key if args.api_key else None,
            testnet_api_secret=api_secret if api_secret not in (None, "") else None,
        ),
    )
    print(f"Updated: {config_path} ([binance_testnet])")
    return 0


def cmd_exchange_ping(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    try:
        client.ping()
    except BinanceAPIError as e:
        print(str(e))
        return 2
    print("OK")
    return 0


def cmd_exchange_time(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    try:
        t = client.get_server_time_ms()
    except BinanceAPIError as e:
        print(str(e))
        return 2
    print(t)
    return 0


def cmd_exchange_info(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    try:
        info = client.get_exchange_info(symbol=args.symbol)
    except BinanceAPIError as e:
        print(str(e))
        return 2
    # Avoid dumping the entire response by default; keep it human-friendly.
    tz = info.get("timezone")
    server_time = info.get("serverTime")
    symbols = info.get("symbols")
    count = len(symbols) if isinstance(symbols, list) else None
    print(f"timezone={tz} serverTime={server_time} symbols={count}")
    return 0


def cmd_exchange_balances(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    try:
        balances = client.get_balances()
    except BinanceAPIError as e:
        print(str(e))
        return 2
    # Print only non-zero balances unless --all is specified.
    shown = 0
    for b in balances:
        if not args.all and b.free in ("0", "0.0", "0.00000000") and b.locked in ("0", "0.0", "0.00000000"):
            continue
        print(f"{b.asset}: free={b.free} locked={b.locked}")
        shown += 1
    if shown == 0:
        print("(no balances to show)")
    return 0


def cmd_sync_startup(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        result = startup_sync(client=client, conn=conn)
    if result.status != "ok":
        print("ERROR (see `show audit` and `status`)")
        return 2
    print(f"OK kind={result.kind} balances={result.balances_upserted} open_orders={result.open_orders_seen}")
    return 0


def cmd_sync_balances(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        result = sync_balances(client=client, conn=conn)
    if result.status != "ok":
        print("ERROR (see `show audit` and `status`)")
        return 2
    print(f"OK kind={result.kind} balances={result.balances_upserted}")
    return 0


def cmd_sync_open_orders(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        result = sync_open_orders(client=client, conn=conn, symbol=args.symbol)
    if result.status != "ok":
        print("ERROR (see `show audit` and `status`)")
        return 2
    print(f"OK kind={result.kind} open_orders={result.open_orders_seen}")
    return 0


def cmd_show_balances(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        rows = state.list_balances(include_zero=args.all, limit=args.limit)
    if getattr(args, "filter", None):
        flt = str(args.filter).strip().upper()
        if flt:
            rows = [r for r in rows if flt in str(r.get("asset", "")).upper()]
    if not rows:
        print("(no balances cached)")
        return 0

    def _d(v: object) -> Decimal:
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal(0)

    updated = [r.get("updated_at_utc") for r in rows if r.get("updated_at_utc")]
    last_updated = max(updated) if updated else None

    print(f"Cached balances: {len(rows)}" + (f" (last updated: {last_updated})" if last_updated else ""))
    print(f"{'ASSET':<12} {'FREE':>18} {'LOCKED':>18} {'UPDATED (UTC)':>22}")
    for r in rows:
        asset = str(r.get("asset") or "")
        free = _d(r.get("free"))
        locked = _d(r.get("locked"))
        updated_at = str(r.get("updated_at_utc") or "")
        free_s = format(free, "f")
        locked_s = format(locked, "f")
        print(f"{asset:<12} {free_s:>18} {locked_s:>18} {updated_at:>22}")
    return 0


def cmd_show_open_orders(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        rows = state.list_open_orders(symbol=args.symbol, limit=args.limit)
    if not rows:
        print("(no open orders cached)")
        return 0
    for r in rows:
        print(
            f"{r['symbol']} {r['side']} {r['type']} status={r['status']} "
            f"price={r['price']} qty={r['quantity']} filled={r['filled_quantity']} "
            f"updated={r['updated_at_utc']} id={r['exchange_order_id']}"
        )
    return 0


def cmd_show_audit(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        rows = state.list_audit_logs(limit=args.limit)
    if not rows:
        print("(no audit logs)")
        return 0
    for r in rows:
        details = r.get("details_json")
        details_s = f" details={details}" if details not in (None, "", "{}") else ""
        print(f"{r['created_at_utc']} {r['level']} {r['event']}{details_s}")
    return 0


def _prompt(text: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else (default or "")


def _prompt_yes_no(text: str, *, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    v = input(f"{text} ({hint}): ").strip().lower()
    if not v:
        return default
    return v in ("y", "yes", "1", "true", "on")

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _style(text: str, *, fg: str | None = None, bold: bool = False) -> str:
    if not _supports_color():
        return text
    codes: list[str] = []
    if bold:
        codes.append("1")
    if fg:
        codes.append(
            {
                "red": "31",
                "green": "32",
                "yellow": "33",
                "blue": "34",
                "magenta": "35",
                "cyan": "36",
                "gray": "90",
            }[fg]
        )
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def cmd_menu(args: argparse.Namespace) -> int:
    """
    Interactive wrapper over subcommands (menu UI).
    Business logic stays in the same command handlers used by non-interactive CLI.
    """
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    mode = "TESTNET" if cfg.binance_testnet else "MAINNET"

    print()
    print(_style(f"CryptoGent Menu  |  Network: {mode}  |  Base URL: {cfg.binance_base_url}", fg="cyan", bold=True))

    def _net_ns(**kwargs) -> argparse.Namespace:
        # For menu actions that touch the exchange. Defaults are safe.
        return argparse.Namespace(
            config=args.config,
            db=args.db,
            ca_bundle=None,
            insecure=False,
            testnet=False,
            base_url=None,
            **kwargs,
        )

    last_trade_request_id: int | None = None
    last_trade_plan_id: int | None = None
    last_candidate_id: int | None = None

    while True:
        print()
        print(_style(" 1) ", fg="yellow", bold=True) + "Setup")
        print(_style(" 2) ", fg="yellow", bold=True) + "Status")
        print(_style(" 3) ", fg="yellow", bold=True) + "Config")
        print(_style(" 4) ", fg="yellow", bold=True) + "Exchange")
        print(_style(" 5) ", fg="yellow", bold=True) + "Sync")
        print(_style(" 6) ", fg="yellow", bold=True) + "Show (cached)")
        print(_style(" 7) ", fg="yellow", bold=True) + "Trade")
        print(_style(" 8) ", fg="yellow", bold=True) + "Exit")

        choice = input("> ").strip()

        if choice == "1":
            print()
            print(_style("Setup", fg="cyan", bold=True))
            print(" 1) Init (create config + DB)")
            print(" 2) Back")
            sub = input("> ").strip()
            if sub == "1":
                cmd_init(argparse.Namespace(config=args.config, db=args.db))
            continue

        if choice == "2":
            cmd_status(argparse.Namespace(config=args.config, db=args.db))
            continue

        if choice == "3":
            while True:
                print()
                print(_style("Config", fg="cyan", bold=True))
                print(" 1) Show config")
                print(" 2) Use testnet")
                print(" 3) Use mainnet")
                print(" 4) Set mainnet API key/secret (plaintext)")
                print(" 5) Set testnet API key/secret (plaintext)")
                print(" 6) Back")
                sub = input("> ").strip()
                if sub == "1":
                    cmd_config_show(argparse.Namespace(config=args.config, db=args.db))
                elif sub == "2":
                    cmd_config_use_testnet(argparse.Namespace(config=args.config, db=args.db))
                    print(_style("Switched to TESTNET (restart menu header to refresh).", fg="green"))
                elif sub == "3":
                    cmd_config_use_mainnet(argparse.Namespace(config=args.config, db=args.db))
                    print(_style("Switched to MAINNET (restart menu header to refresh).", fg="green"))
                elif sub == "4":
                    api_key = _prompt("BINANCE_API_KEY", default="")
                    api_secret = _prompt("BINANCE_API_SECRET", default="")
                    if not _prompt_yes_no("Store in cryptogent.toml as plaintext?", default=False):
                        continue
                    cmd_config_set_binance(
                        argparse.Namespace(
                            config=args.config,
                            db=args.db,
                            api_key=api_key,
                            api_secret=api_secret,
                            api_secret_stdin=False,
                            testnet=False,
                            base_url=None,
                        )
                    )
                elif sub == "5":
                    api_key = _prompt("BINANCE_TESTNET_API_KEY", default="")
                    api_secret = _prompt("BINANCE_TESTNET_API_SECRET", default="")
                    if not _prompt_yes_no("Store in cryptogent.toml as plaintext?", default=False):
                        continue
                    cmd_config_set_binance_testnet(
                        argparse.Namespace(
                            config=args.config,
                            db=args.db,
                            api_key=api_key,
                            api_secret=api_secret,
                            api_secret_stdin=False,
                        )
                    )
                elif sub == "6":
                    break
                else:
                    print(_style("Invalid choice", fg="red"))
            continue

        if choice == "4":
            while True:
                print()
                print(_style("Exchange (no trading)", fg="cyan", bold=True))
                print(" 1) Ping")
                print(" 2) Time")
                print(" 3) Exchange info")
                print(" 4) Balances (auth)")
                print(" 5) Back")
                sub = input("> ").strip()
                if sub == "1":
                    cmd_exchange_ping(_net_ns())
                elif sub == "2":
                    cmd_exchange_time(_net_ns())
                elif sub == "3":
                    sym = _prompt("Symbol (optional)", default="").upper().strip() or None
                    cmd_exchange_info(_net_ns(symbol=sym))
                elif sub == "4":
                    show_all = _prompt_yes_no("Include zero balances?", default=False)
                    cmd_exchange_balances(_net_ns(all=show_all))
                elif sub == "5":
                    break
                else:
                    print(_style("Invalid choice", fg="red"))
            continue

        if choice == "5":
            while True:
                print()
                print(_style("Sync (writes to SQLite)", fg="cyan", bold=True))
                print(" 1) Startup sync")
                print(" 2) Sync balances")
                print(" 3) Sync open orders")
                print(" 4) Back")
                sub = input("> ").strip()
                if sub == "1":
                    cmd_sync_startup(_net_ns())
                elif sub == "2":
                    cmd_sync_balances(_net_ns())
                elif sub == "3":
                    sym = _prompt("Symbol (optional)", default="").upper().strip() or None
                    cmd_sync_open_orders(_net_ns(symbol=sym))
                elif sub == "4":
                    break
                else:
                    print(_style("Invalid choice", fg="red"))
            continue

        if choice == "6":
            while True:
                print()
                print(_style("Show (cached; no network)", fg="cyan", bold=True))
                print(" 1) Show balances")
                print(" 2) Show open orders")
                print(" 3) Show audit logs")
                print(" 4) Back")
                sub = input("> ").strip()
                if sub == "1":
                    limit_s = _prompt("How many rows?", default="25")
                    flt = _prompt("Filter by asset substring (optional)", default="").strip() or None
                    include_zero = _prompt_yes_no("Include zero balances?", default=False)
                    cmd_show_balances(argparse.Namespace(config=args.config, db=args.db, all=include_zero, limit=int(limit_s), filter=flt))
                elif sub == "2":
                    sym = _prompt("Symbol (optional)", default="").upper().strip() or None
                    limit_s = _prompt("How many rows?", default="50")
                    cmd_show_open_orders(argparse.Namespace(config=args.config, db=args.db, symbol=sym, limit=int(limit_s)))
                elif sub == "3":
                    limit_s = _prompt("How many entries?", default="50")
                    cmd_show_audit(argparse.Namespace(config=args.config, db=args.db, limit=int(limit_s)))
                elif sub == "4":
                    break
                else:
                    print(_style("Invalid choice", fg="red"))
            continue

        if choice == "7":
            while True:
                print()
                print(_style("Trade (requests; no execution)", fg="cyan", bold=True))
                print(" 1) Start trade (create request)")
                print(" 2) List trade requests")
                print(" 3) Show trade request")
                print(" 4) Cancel trade request")
                print(" 5) Validate trade request")
                print(" 6) Build trade plan (from request)")
                print(" 7) List trade plans")
                print(" 8) Show trade plan")
                print(" 9) Safety validate trade plan")
                print("10) Execute trade candidate (Phase 7)")
                print("11) List executions")
                print("12) Show execution")
                print("13) Cancel LIMIT execution")
                print("14) Back")
                sub = input("> ").strip()

                if sub == "1":
                    while True:
                        paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
                        config_path = ensure_default_config(paths.config_path)
                        cfg = load_config(config_path)

                        profit_target_pct = _prompt("Profit target (%)", default="2.0")
                        stop_loss_pct = _prompt("Stop-loss (%)", default=str(cfg.trading_default_stop_loss_pct))
                        deadline_hours = _prompt("Deadline (hours from now)", default="24")
                        budget_mode = _prompt("Budget mode (manual/auto)", default=str(cfg.trading_default_budget_mode)).lower()
                        budget = _prompt("Budget amount (e.g. 50)", default="50")
                        budget_asset = _prompt("Budget asset (e.g. USDT)", default="USDT").upper()
                        symbol = _prompt("Preferred symbol (e.g. BTCUSDT)", default="BTCUSDT").upper()
                        exit_asset = _prompt("Exit asset", default=str(cfg.trading_default_exit_asset)).upper()
                        label = _prompt("Label (optional)", default="").strip() or None
                        notes = _prompt("Notes (optional)", default="").strip() or None

                        try:
                            validate_trade_request(
                                profit_target_pct=profit_target_pct,
                                stop_loss_pct=stop_loss_pct,
                                deadline=None,
                                deadline_minutes=None,
                                deadline_hours=int(deadline_hours),
                                budget_mode=budget_mode,
                                budget_asset=budget_asset,
                                budget_amount=budget if budget_mode == "manual" else None,
                                preferred_symbol=symbol,
                                exit_asset=exit_asset,
                                label=label,
                                notes=notes,
                            )
                        except ValidationError as e:
                            print(f"Invalid input: {e}")
                            if not _prompt_yes_no("Try again?", default=True):
                                break
                            continue

                        cmd_trade_start(
                            argparse.Namespace(
                                config=args.config,
                                db=args.db,
                                profit_target_pct=profit_target_pct,
                                stop_loss_pct=stop_loss_pct,
                                deadline=None,
                                deadline_minutes=None,
                                deadline_hours=int(deadline_hours),
                                budget_mode=budget_mode,
                                budget=budget if budget_mode == "manual" else None,
                                budget_asset=budget_asset,
                                symbol=symbol,
                                exit_asset=exit_asset,
                                label=label,
                                notes=notes,
                                yes=True,
                            )
                        )
                        try:
                            db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
                            with connect(db_path) as conn:
                                row = conn.execute("SELECT id FROM trade_requests ORDER BY id DESC LIMIT 1").fetchone()
                                last_trade_request_id = int(row[0]) if row else None
                        except Exception:
                            last_trade_request_id = None

                        if last_trade_request_id is not None and _prompt_yes_no("Validate this request now?", default=False):
                            cmd_trade_validate(_net_ns(id=last_trade_request_id))
                        break
                    continue

                if sub == "2":
                    limit_s = _prompt("Limit rows", default="20")
                    cmd_trade_list(argparse.Namespace(config=args.config, db=args.db, limit=int(limit_s)))
                    continue

                if sub == "3":
                    tid = _prompt("Trade request id", default=str(last_trade_request_id or "")).strip()
                    if not tid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_show(argparse.Namespace(config=args.config, db=args.db, id=int(tid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "4":
                    tid = _prompt("Trade request id", default=str(last_trade_request_id or "")).strip()
                    if not tid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_cancel(argparse.Namespace(config=args.config, db=args.db, id=int(tid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "5":
                    tid = _prompt("Trade request id", default=str(last_trade_request_id or "")).strip()
                    if not tid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_validate(_net_ns(id=int(tid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "6":
                    tid = _prompt("Trade request id", default=str(last_trade_request_id or "")).strip()
                    if not tid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_plan(_net_ns(id=int(tid), candle_interval="5m", candle_count=288))
                        try:
                            db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
                            with connect(db_path) as conn:
                                row = conn.execute("SELECT id FROM trade_plans ORDER BY id DESC LIMIT 1").fetchone()
                                last_trade_plan_id = int(row[0]) if row else None
                        except Exception:
                            last_trade_plan_id = None
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "7":
                    limit_s = _prompt("Limit rows", default="20")
                    cmd_trade_plan_list(argparse.Namespace(config=args.config, db=args.db, limit=int(limit_s)))
                    continue

                if sub == "8":
                    pid = _prompt("Trade plan id", default=str(last_trade_plan_id or "")).strip()
                    if not pid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_plan_show(argparse.Namespace(config=args.config, db=args.db, plan_id=int(pid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "9":
                    pid = _prompt("Trade plan id", default=str(last_trade_plan_id or "")).strip()
                    if not pid:
                        print(_style("No id provided", fg="red"))
                        continue
                    order_type = _prompt("Order type (MARKET_BUY/LIMIT_BUY)", default="MARKET_BUY").strip().upper()
                    limit_price = None
                    if order_type == "LIMIT_BUY":
                        limit_price = _prompt("Limit price", default="").strip() or None
                    try:
                        cmd_trade_safety(
                            _net_ns(
                                plan_id=int(pid),
                                max_age_minutes=60,
                                price_drift_warn_pct="1.0",
                                price_drift_unsafe_pct="3.0",
                                max_position_pct="25",
                                max_stop_loss_pct="10",
                                order_type=order_type,
                                limit_price=limit_price,
                            )
                        )
                        try:
                            db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
                            with connect(db_path) as conn:
                                row = conn.execute(
                                    "SELECT id FROM execution_candidates ORDER BY id DESC LIMIT 1"
                                ).fetchone()
                                last_candidate_id = int(row[0]) if row else None
                        except Exception:
                            last_candidate_id = None
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "10":
                    cid = _prompt("Candidate id", default=str(last_candidate_id or "")).strip()
                    if not cid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_execute(_net_ns(candidate_id=int(cid), yes=False))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "11":
                    limit_s = _prompt("Limit rows", default="20")
                    cmd_trade_executions_list(argparse.Namespace(config=args.config, db=args.db, limit=int(limit_s)))
                    continue

                if sub == "12":
                    eid = _prompt("Execution id", default="").strip()
                    if not eid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_executions_show(argparse.Namespace(config=args.config, db=args.db, execution_id=int(eid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "13":
                    eid = _prompt("Execution id", default="").strip()
                    if not eid:
                        print(_style("No id provided", fg="red"))
                        continue
                    try:
                        cmd_trade_execution_cancel(_net_ns(execution_id=int(eid)))
                    except ValueError:
                        print(_style("Invalid id", fg="red"))
                    continue

                if sub == "14":
                    break
                print(_style("Invalid choice", fg="red"))
            continue

        if choice == "8":
            return 0

        print(_style("Invalid choice", fg="red"))


def cmd_trade_start(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    budget_mode = args.budget_mode or cfg.trading_default_budget_mode
    exit_asset = args.exit_asset or cfg.trading_default_exit_asset
    stop_loss_default = cfg.trading_default_stop_loss_pct

    try:
        req = validate_trade_request(
            profit_target_pct=args.profit_target_pct,
            stop_loss_pct=args.stop_loss_pct or stop_loss_default,
            deadline=args.deadline,
            deadline_minutes=args.deadline_minutes,
            deadline_hours=args.deadline_hours,
            budget_mode=budget_mode,
            budget_asset=args.budget_asset,
            budget_amount=args.budget,
            preferred_symbol=args.symbol,
            exit_asset=exit_asset,
            label=args.label,
            notes=args.notes,
        )
    except ValidationError as e:
        print(f"Invalid trade request: {e}")
        return 2

    # Confirmation step (interactive unless --yes).
    if not getattr(args, "yes", False):
        print("Trade Request Summary")
        print(f"- Target Profit: {req.profit_target_pct}%")
        print(f"- Stop-Loss: {req.stop_loss_pct}%")
        print(f"- Deadline: {req.deadline_utc.isoformat()}")
        print(f"- Budget Mode: {req.budget_mode}")
        if req.budget_mode == "manual":
            print(f"- Budget: {req.budget_amount} {req.budget_asset}")
        else:
            print(f"- Budget Asset: {req.budget_asset}")
        print(f"- Preferred Symbol: {req.preferred_symbol}")
        print(f"- Exit Asset: {req.exit_asset}")
        if req.label:
            print(f"- Label: {req.label}")
        if req.notes:
            print(f"- Notes: {req.notes}")
        if not _prompt_yes_no("Confirm?", default=False):
            print("Cancelled")
            return 2

    with connect(db_path) as conn:
        state = StateManager(conn)
        trade_id = state.create_trade_request(req)
    print(f"Created trade request id={trade_id} status=DRAFT")
    return 0


def cmd_trade_list(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        rows = state.list_trade_requests(limit=args.limit)
    if not rows:
        print("(no trade requests)")
        return 0

    def _cell(v: object, width: int) -> str:
        s = "" if v is None else str(v)
        if len(s) > width:
            return s[: max(0, width - 1)] + "…"
        return s

    print(f"Trade requests: {len(rows)}")
    print(
        f"{'ID':>4} {'REQUEST_ID':<10} {'STATUS':<9} {'SYMBOL':<10} {'BUDGET':<16} "
        f"{'PT%':>6} {'SL%':>6} {'DEADLINE (UTC)':<22} {'VALID':<7}"
    )
    for r in rows:
        status = r.get("status")
        status_display = "DRAFT" if status == "NEW" else status
        budget_mode = (r.get("budget_mode") or "").upper()
        budget_amt = r.get("budget_amount")
        budget_asset = r.get("budget_asset")
        budget_display = f"{budget_mode}:{budget_amt} {budget_asset}" if budget_amt is not None else f"{budget_mode}:{budget_asset}"

        print(
            f"{int(r['id']):>4} "
            f"{_cell(r.get('request_id') or '-', 10):<10} "
            f"{_cell(status_display or '-', 9):<9} "
            f"{_cell(r.get('preferred_symbol') or '-', 10):<10} "
            f"{_cell(budget_display, 16):<16} "
            f"{_cell(str(r.get('profit_target_pct') or ''), 6):>6} "
            f"{_cell(str(r.get('stop_loss_pct') or ''), 6):>6} "
            f"{_cell(r.get('deadline_utc') or '-', 22):<22} "
            f"{_cell(r.get('validation_status') or '-', 7):<7}"
        )
    return 0


def cmd_trade_show(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        row = state.get_trade_request(args.id)
    if not row:
        print("(not found)")
        return 2
    print(f"id={row['id']}")
    print(f"request_id={row.get('request_id')}")
    status = row.get("status")
    print(f"status={'DRAFT' if status == 'NEW' else status}")
    print(f"preferred_symbol={row['preferred_symbol']}")
    if "budget_mode" in row:
        print(f"budget_mode={row.get('budget_mode')}")
    print(f"budget={row['budget_amount']} {row['budget_asset']}")
    if "exit_asset" in row:
        print(f"exit_asset={row.get('exit_asset')}")
    if "label" in row:
        print(f"label={row.get('label')}")
    if "notes" in row:
        print(f"notes={row.get('notes')}")
    print(f"profit_target_pct={row['profit_target_pct']}")
    print(f"stop_loss_pct={row['stop_loss_pct']}")
    if "deadline_hours" in row:
        print(f"deadline_hours={row.get('deadline_hours')}")
    print(f"deadline_utc={row['deadline_utc']}")
    if "validation_status" in row:
        print(f"validation_status={row.get('validation_status')}")
        print(f"validation_error={row.get('validation_error')}")
        print(f"validated_at_utc={row.get('validated_at_utc')}")
        print(f"last_price={row.get('last_price')}")
        print(f"estimated_qty={row.get('estimated_qty')}")
        print(f"symbol_base_asset={row.get('symbol_base_asset')}")
        print(f"symbol_quote_asset={row.get('symbol_quote_asset')}")
    print(f"created_at_utc={row['created_at_utc']}")
    print(f"updated_at_utc={row['updated_at_utc']}")
    return 0


def cmd_trade_cancel(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        state = StateManager(conn)
        ok = state.cancel_trade_request(args.id)
    if not ok:
        print("Not cancelled (not found or not NEW)")
        return 2
    print("Cancelled")
    return 0


def cmd_trade_validate(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    with connect(db_path) as conn:
        state = StateManager(conn)
        row = state.get_trade_request(args.id)
        if not row:
            print("(not found)")
            return 2
        if row.get("status") in ("CANCELLED",):
            print(f"Trade request is CANCELLED; not validating.")
            return 2
        symbol = row.get("preferred_symbol")
        if not symbol:
            print("Trade request has no preferred_symbol; set one when creating the request.")
            return 2
        deadline_s = str(row.get("deadline_utc") or "")
        try:
            deadline = datetime.fromisoformat(deadline_s.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            print("Invalid stored deadline_utc")
            return 2
        if deadline <= datetime.now(UTC):
            err = "deadline already passed"
            with connect(db_path) as conn2:
                StateManager(conn2).set_trade_request_validation(
                    trade_request_id=args.id,
                    validation_status="INVALID",
                    validation_error=err,
                    last_price=None,
                    estimated_qty=None,
                    symbol_base_asset=None,
                    symbol_quote_asset=None,
                )
            print(f"INVALID: {err}")
            return 2
        budget_asset = str(row.get("budget_asset") or "")
        try:
            budget_amount = Decimal(str(row.get("budget_amount")))
        except (InvalidOperation, ValueError):
            print("Invalid stored budget_amount")
            return 2
        try:
            profit_target_pct = Decimal(str(row.get("profit_target_pct")))
            stop_loss_pct = Decimal(str(row.get("stop_loss_pct")))
        except (InvalidOperation, ValueError):
            profit_target_pct = None
            stop_loss_pct = None
        deadline_hours = int(row.get("deadline_hours") or 0)

    try:
        info = client.get_symbol_info(symbol=str(symbol))
        if not info:
            err = "symbol not found in exchangeInfo"
            with connect(db_path) as conn:
                StateManager(conn).set_trade_request_validation(
                    trade_request_id=args.id,
                    validation_status="INVALID",
                    validation_error=err,
                    last_price=None,
                    estimated_qty=None,
                    symbol_base_asset=None,
                    symbol_quote_asset=None,
                )
            print(f"INVALID: {err}")
            return 2

        rules = parse_symbol_rules(info)
        price_s = client.get_ticker_price(symbol=rules.symbol)
        last_price = Decimal(price_s)
        res = precheck_market_buy(
            rules=rules,
            budget_asset=budget_asset,
            budget_amount=budget_amount,
            last_price=last_price,
        )
    except (BinanceAPIError, RuleError, InvalidOperation, ValueError) as e:
        err = str(e)
        with connect(db_path) as conn:
            StateManager(conn).set_trade_request_validation(
                trade_request_id=args.id,
                validation_status="ERROR",
                validation_error=err,
                last_price=None,
                estimated_qty=None,
                symbol_base_asset=None,
                symbol_quote_asset=None,
            )
        print(f"ERROR: {err}")
        return 2

    with connect(db_path) as conn:
        ok = StateManager(conn).set_trade_request_validation(
            trade_request_id=args.id,
            validation_status="VALID" if res.ok else "INVALID",
            validation_error=res.error,
            last_price=str(last_price),
            estimated_qty=str(res.estimated_qty) if res.estimated_qty is not None else None,
            symbol_base_asset=rules.base_asset,
            symbol_quote_asset=rules.quote_asset,
        )
    if not ok:
        print("Not updated (trade request not found or not NEW)")
        return 2

    if res.ok:
        # Feasibility gate (planning-oriented). Validation is only VALID if feasibility can be computed and is not_feasible.
        if profit_target_pct is None or stop_loss_pct is None or deadline_hours <= 0:
            err = "missing_trade_request_fields_for_feasibility"
            with connect(db_path) as conn:
                StateManager(conn).set_trade_request_validation(
                    trade_request_id=args.id,
                    validation_status="ERROR",
                    validation_error=err,
                    last_price=str(last_price),
                    estimated_qty=str(res.estimated_qty) if res.estimated_qty is not None else None,
                    symbol_base_asset=rules.base_asset,
                    symbol_quote_asset=rules.quote_asset,
                )
            print(f"ERROR: {err}")
            return 2

        try:
            market_client = BinanceSpotClient(
                base_url=BINANCE_SPOT_BASE_URL,
                api_key=None,
                api_secret=None,
                recv_window_ms=client.recv_window_ms,
                timeout_s=client.timeout_s,
                tls_verify=client.tls_verify,
                ca_bundle_path=client.ca_bundle_path,
            )
            snapshot = fetch_market_snapshot(
                client=market_client,
                symbol=rules.symbol,
                candle_interval="5m",
                candle_count=288,
                fetch_book_ticker=True,
            )
            md_warnings, hard = freshness_and_consistency_checks(snapshot=snapshot, candle_interval="5m", candle_count=288)
            if hard:
                feas_category = "not_feasible"
                feas_reason = hard
                feas_warnings = md_warnings
            else:
                spread_available = snapshot.bid is not None and snapshot.ask is not None and snapshot.spread_pct is not None
                feas = evaluate_feasibility(
                    profit_target_pct=profit_target_pct,
                    stop_loss_pct=stop_loss_pct,
                    deadline_hours=deadline_hours,
                    volume_24h_quote=snapshot.volume_24h_quote,
                    volatility_pct=snapshot.candles.volatility_pct,
                    spread_pct=snapshot.spread_pct,
                    spread_available=spread_available,
                    warnings=md_warnings,
                )
                feas_category = feas.category
                feas_reason = feas.rejection_reason
                feas_warnings = feas.warnings
        except (BinanceAPIError, MarketDataError, FeasibilityError, ValueError) as e:
            err = f"feasibility_unavailable: {e}"
            with connect(db_path) as conn:
                StateManager(conn).set_trade_request_validation(
                    trade_request_id=args.id,
                    validation_status="ERROR",
                    validation_error=err,
                    last_price=str(last_price),
                    estimated_qty=str(res.estimated_qty) if res.estimated_qty is not None else None,
                    symbol_base_asset=rules.base_asset,
                    symbol_quote_asset=rules.quote_asset,
                )
            print(f"ERROR: {err}")
            return 2

        if feas_category == "not_feasible":
            err = f"not_feasible: {feas_reason or 'unknown'}"
            with connect(db_path) as conn:
                StateManager(conn).set_trade_request_validation(
                    trade_request_id=args.id,
                    validation_status="INVALID",
                    validation_error=err,
                    last_price=str(last_price),
                    estimated_qty=str(res.estimated_qty) if res.estimated_qty is not None else None,
                    symbol_base_asset=rules.base_asset,
                    symbol_quote_asset=rules.quote_asset,
                )
            warnings_s = ",".join(feas_warnings) if feas_warnings else "-"
            print(
                f"INVALID: {err} (symbol={rules.symbol} price={last_price} est_qty={res.estimated_qty} notional={res.notional} warnings={warnings_s})"
            )
            return 2

        extra = None
        if feas_category in ("feasible_with_warning", "high_risk"):
            warnings_s = ",".join(feas_warnings) if feas_warnings else "-"
            extra = f"feasibility={feas_category}; warnings={warnings_s}"

        with connect(db_path) as conn:
            StateManager(conn).set_trade_request_validation(
                trade_request_id=args.id,
                validation_status="VALID",
                validation_error=extra,
                last_price=str(last_price),
                estimated_qty=str(res.estimated_qty) if res.estimated_qty is not None else None,
                symbol_base_asset=rules.base_asset,
                symbol_quote_asset=rules.quote_asset,
            )

        print(f"VALID: symbol={rules.symbol} price={last_price} est_qty={res.estimated_qty} notional={res.notional} {rules.quote_asset}")
        if extra:
            print(f"FEASIBILITY: {extra} market_data_env=mainnet_public")
        else:
            print("FEASIBILITY: feasible market_data_env=mainnet_public")
        return 0
    print(
        f"INVALID: {res.error} (symbol={rules.symbol} price={last_price} est_qty={res.estimated_qty} notional={res.notional})"
    )
    return 2


def cmd_trade_plan(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    with connect(db_path) as conn:
        state = StateManager(conn)
        row = state.get_trade_request(args.id)
        if not row:
            print("(not found)")
            return 2
        if row.get("status") in ("CANCELLED",):
            print("Trade request is CANCELLED; not planning.")
            return 2

        try:
            exec_client = _client_from_args(args)
            ca_bundle = args.ca_bundle.expanduser() if getattr(args, "ca_bundle", None) else None
            market_client = BinanceSpotClient(
                base_url=BINANCE_SPOT_BASE_URL,
                api_key=None,
                api_secret=None,
                recv_window_ms=exec_client.recv_window_ms,
                timeout_s=exec_client.timeout_s,
                tls_verify=exec_client.tls_verify,
                ca_bundle_path=ca_bundle,
            )
            exec_env = "testnet" if "testnet.binance.vision" in (exec_client.base_url or "") else "mainnet"
            plan = build_trade_plan(
                cfg=cfg,
                state=state,
                trade_request=row,
                market_client=market_client,
                execution_client=exec_client,
                execution_environment=exec_env,
                candle_interval=str(getattr(args, "candle_interval", "5m")),
                candle_count=int(getattr(args, "candle_count", 288)),
            )
            plan_id = persist_trade_plan(state=state, plan=plan)
        except (PlanningError, BinanceAPIError, RuleError, ValueError) as e:
            err = str(e)
            state.append_audit(level="ERROR", event="trade_plan_failed", details={"trade_request_id": int(args.id), "error": err})
            print(f"ERROR: {err}")
            return 2

    print("Trade Planning Summary")
    print(f"- Plan ID: {plan_id}")
    print(f"- Trade Request ID: {plan.trade_request_id}")
    if plan.request_id:
        print(f"- Request ID: {plan.request_id}")
    print(f"- Market Data Env: {plan.market_data_environment}")
    print(f"- Execution Env: {plan.execution_environment}")
    print(f"- Symbol: {plan.symbol}")
    print(f"- Feasibility: {plan.feasibility_category}")
    if plan.approved_budget_amount is not None:
        print(f"- Budget Approved: {plan.approved_budget_amount} {plan.approved_budget_asset}")
    if plan.usable_budget_amount is not None:
        print(f"- Budget Usable: {plan.usable_budget_amount} {plan.approved_budget_asset}")
    if plan.rounded_quantity is not None and plan.expected_notional is not None:
        print(f"- Est. Qty: {plan.rounded_quantity} ({plan.expected_notional} {plan.approved_budget_asset})")
    print(f"- Signal: {plan.signal.upper()} (confidence={plan.signal_confidence})")
    if plan.warnings:
        print("- Warnings:")
        for w in plan.warnings:
            print(f"  - {w}")
    return 0 if plan.feasibility_category != "not_feasible" else 2


def cmd_trade_plan_list(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        rows = StateManager(conn).list_trade_plans(limit=int(getattr(args, "limit", 20)))
    if not rows:
        print("(no trade plans)")
        return 0

    def _cell(v: object, width: int) -> str:
        s = "" if v is None else str(v)
        if len(s) > width:
            return s[: max(0, width - 1)] + "…"
        return s

    print(f"Trade plans: {len(rows)}")
    print(
        f"{'PLAN_ID':>7} {'REQ_ID':<10} {'TR_ID':>5} {'SYMBOL':<10} {'CATEGORY':<18} "
        f"{'BUDGET':<16} {'STATUS':<18} {'WARN':>4} {'CREATED (UTC)':<22}"
    )
    for r in rows:
        warnings_json = r.get("warnings_json") or "[]"
        warn_n = 0
        try:
            import json as _json

            parsed = _json.loads(warnings_json)
            warn_n = len(parsed) if isinstance(parsed, list) else 0
        except Exception:
            warn_n = 0
        budget_amt = r.get("approved_budget_amount")
        budget_asset = r.get("approved_budget_asset")
        budget_display = f"{budget_amt} {budget_asset}" if budget_amt is not None else f"{budget_asset}"
        print(
            f"{int(r['id']):>7} "
            f"{_cell(r.get('request_id') or '-', 10):<10} "
            f"{int(r.get('trade_request_id') or 0):>5} "
            f"{_cell(r.get('symbol') or '-', 10):<10} "
            f"{_cell(r.get('feasibility_category') or '-', 18):<18} "
            f"{_cell(budget_display, 16):<16} "
            f"{_cell(r.get('status') or '-', 18):<18} "
            f"{warn_n:>4} "
            f"{_cell(r.get('created_at_utc') or '-', 22):<22}"
        )
    return 0


def cmd_trade_plan_show(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        row = StateManager(conn).get_trade_plan(plan_id=int(args.plan_id))
    if not row:
        print("(not found)")
        return 2
    print(f"plan_id={row.get('id')}")
    print(f"trade_request_id={row.get('trade_request_id')}")
    print(f"request_id={row.get('request_id')}")
    print(f"status={row.get('status')}")
    print(f"feasibility_category={row.get('feasibility_category')}")
    print(f"warnings_json={row.get('warnings_json')}")
    print(f"rejection_reason={row.get('rejection_reason')}")
    print(f"market_data_environment={row.get('market_data_environment')}")
    print(f"execution_environment={row.get('execution_environment')}")
    print(f"symbol={row.get('symbol')}")
    print(f"price={row.get('price')}")
    print(f"bid={row.get('bid')}")
    print(f"ask={row.get('ask')}")
    print(f"spread_pct={row.get('spread_pct')}")
    print(f"volume_24h_quote={row.get('volume_24h_quote')}")
    print(f"volatility_pct={row.get('volatility_pct')}")
    print(f"momentum_pct={row.get('momentum_pct')}")
    print(f"budget_mode={row.get('budget_mode')}")
    print(f"approved_budget={row.get('approved_budget_amount')} {row.get('approved_budget_asset')}")
    print(f"usable_budget_amount={row.get('usable_budget_amount')}")
    print(f"raw_quantity={row.get('raw_quantity')}")
    print(f"rounded_quantity={row.get('rounded_quantity')}")
    print(f"expected_notional={row.get('expected_notional')}")
    print(f"signal={row.get('signal')}")
    print(f"signal_reasons_json={row.get('signal_reasons_json')}")
    print(f"rules_snapshot_json={row.get('rules_snapshot_json')}")
    print(f"market_summary_json={row.get('market_summary_json')}")
    print(f"candidate_list_json={row.get('candidate_list_json')}")
    print(f"created_at_utc={row.get('created_at_utc')}")
    return 0


def cmd_trade_safety(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    with connect(db_path) as conn:
        state = StateManager(conn)
        plan = state.get_trade_plan(plan_id=int(args.plan_id))
        if not plan:
            print("(not found)")
            return 2
        tr_id = int(plan.get("trade_request_id") or 0)
        trade_request = state.get_trade_request(tr_id)
        if not trade_request:
            print("Missing linked trade_request")
            return 2

        order_type = str(getattr(args, "order_type", "MARKET_BUY")).strip().upper()
        limit_price_s = getattr(args, "limit_price", None)
        limit_price = None
        if limit_price_s not in (None, ""):
            try:
                limit_price = Decimal(str(limit_price_s))
            except Exception:
                limit_price = None

        try:
            decision = evaluate_safety(
                state=state,
                execution_client=client,
                plan=plan,
                trade_request=trade_request,
                order_type=order_type,
                limit_price=limit_price,
                max_plan_age_minutes=int(getattr(args, "max_age_minutes", 60)),
                max_price_drift_warning_pct=Decimal(str(getattr(args, "price_drift_warn_pct", "1.0"))),
                max_price_drift_unsafe_pct=Decimal(str(getattr(args, "price_drift_unsafe_pct", "3.0"))),
                max_position_pct=Decimal(str(getattr(args, "max_position_pct", "25"))),
                max_stop_loss_pct=Decimal(str(getattr(args, "max_stop_loss_pct", "10"))),
            )
        except (SafetyError, BinanceAPIError, InvalidOperation, ValueError) as e:
            err = str(e)
            state.append_audit(level="ERROR", event="trade_safety_failed", details={"plan_id": int(args.plan_id), "error": err})
            print(f"ERROR: {err}")
            return 2

        details_json = None
        try:
            import json as _json

            details_json = _json.dumps(decision.details, separators=(",", ":"))
        except Exception:
            details_json = None

        candidate_id = state.create_execution_candidate(
            trade_plan_id=int(plan.get("id")),
            trade_request_id=tr_id,
            request_id=plan.get("request_id"),
            symbol=str(plan.get("symbol") or ""),
            side="buy",
            order_type=order_type,
            limit_price=str(limit_price) if limit_price is not None else None,
            execution_environment=str(plan.get("execution_environment") or ""),
            validation_status=decision.validation_status,
            risk_status=decision.risk_status,
            approved_budget_asset=decision.approved_budget_asset,
            approved_budget_amount=str(decision.approved_budget_amount),
            approved_quantity=str(decision.approved_quantity),
            execution_ready=decision.category in ("safe", "safe_with_warning"),
            summary=decision.summary,
            details_json=details_json,
        )

    print("Safety Evaluation Summary")
    print(f"- Plan ID: {int(args.plan_id)}")
    print(f"- Candidate ID: {candidate_id}")
    print(f"- Result: {decision.category}")
    print(f"- Validation: {decision.validation_status}")
    print(f"- Risk: {decision.risk_status}")
    print(f"- Approved Budget: {decision.approved_budget_amount} {decision.approved_budget_asset}")
    print(f"- Approved Quantity: {decision.approved_quantity}")
    if decision.warnings:
        print("- Warnings:")
        for w in decision.warnings:
            print(f"  - {w}")
    if decision.errors:
        print("- Errors:")
        for e in decision.errors:
            print(f"  - {e}")
    print(f"- Summary: {decision.summary}")
    return 0 if decision.category in ("safe", "safe_with_warning") else 2


def cmd_trade_execute(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    runtime_env = "testnet" if cfg.binance_testnet else "mainnet"

    with connect(db_path) as conn:
        state = StateManager(conn)
        cand = state.get_execution_candidate(candidate_id=int(args.candidate_id))
        if not cand:
            print("(not found)")
            return 2

        if state.has_nonterminal_execution_for_candidate(candidate_id=int(args.candidate_id)):
            print("Rejected: this candidate already has an execution attempt (use a new candidate)")
            return 2

        # Hard gates (no execution row for gate failures).
        if int(cand.get("execution_ready") or 0) != 1:
            print("Rejected: execution_ready != 1")
            return 2
        if str(cand.get("risk_status") or "") not in ("approved", "approved_with_warning"):
            print(f"Rejected: risk_status={cand.get('risk_status')}")
            return 2
        if str(cand.get("validation_status") or "") != "passed":
            print(f"Rejected: validation_status={cand.get('validation_status')}")
            return 2

        plan_id = int(cand.get("trade_plan_id") or 0)
        plan = state.get_trade_plan(plan_id=plan_id)
        if not plan:
            print("Rejected: missing linked trade plan")
            return 2

        cand_env = str(cand.get("execution_environment") or "").strip().lower()
        if cand_env not in ("mainnet", "testnet"):
            print("Rejected: invalid candidate execution_environment")
            return 2
        if cand_env != runtime_env:
            print(f"Rejected: environment mismatch candidate={cand_env} runtime={runtime_env}")
            return 2
        plan_env = str(plan.get("execution_environment") or "").strip().lower()
        if plan_env not in ("mainnet", "testnet"):
            print("Rejected: invalid plan execution_environment")
            return 2
        if plan_env != cand_env:
            print(f"Rejected: environment mismatch plan={plan_env} candidate={cand_env}")
            return 2

        # Confirm quote asset matches budget asset via rules snapshot.
        try:
            import json as _json

            rules_snapshot = _json.loads(str(plan.get("rules_snapshot_json") or ""))
        except Exception:
            print("Rejected: missing/invalid rules_snapshot_json")
            return 2
        if not isinstance(rules_snapshot, dict):
            print("Rejected: invalid rules_snapshot_json")
            return 2

        order_type = str(cand.get("order_type") or "").strip().upper()
        limit_price = cand.get("limit_price")
        if order_type not in ("MARKET_BUY", "LIMIT_BUY"):
            print(f"Rejected: invalid order_type={order_type}")
            return 2
        if order_type == "LIMIT_BUY" and (limit_price in (None, "")):
            print("Rejected: LIMIT_BUY requires limit_price in candidate")
            return 2

        # Confirmation prompt (unless --yes).
        if not getattr(args, "yes", False):
            budget_amt = cand.get("approved_budget_amount")
            budget_asset = cand.get("approved_budget_asset")
            sym = cand.get("symbol")
            print("Execution Summary")
            print(f"- Candidate ID: {cand.get('id')}")
            print(f"- Plan ID: {plan_id}")
            print(f"- Symbol: {sym}")
            print(f"- Side: BUY")
            if order_type == "MARKET_BUY":
                print(f"- Type: MARKET BUY (quoteOrderQty)")
            else:
                print(f"- Type: LIMIT BUY (GTC)")
                print(f"- Limit Price: {limit_price}")
            print(f"- Approved Budget: {budget_amt} {budget_asset}")
            print(f"- Environment: {runtime_env}")
            if not _prompt_yes_no("Execute now?", default=False):
                print("Cancelled")
                return 2

        try:
            if order_type == "MARKET_BUY":
                execution_id, outcome = execute_market_buy_quote(
                    execution_client=client,
                    state=state,
                    candidate=cand,
                    plan=plan,
                    rules_snapshot=rules_snapshot,
                    runtime_environment=runtime_env,
                )
            else:
                execution_id, outcome = execute_limit_buy(
                    execution_client=client,
                    state=state,
                    candidate=cand,
                    plan=plan,
                    rules_snapshot=rules_snapshot,
                    runtime_environment=runtime_env,
                )
        except (ExecutionError, BinanceAPIError, ValueError) as e:
            state.append_audit(level="ERROR", event="execution_failed", details={"candidate_id": int(args.candidate_id), "error": str(e)})
            print(f"ERROR: {e}")
            return 2

    print("Execution Result")
    print(f"- Execution ID: {execution_id}")
    print(f"- Candidate ID: {cand.get('id')}")
    print(f"- Status: {outcome.local_status}")
    if outcome.raw_status:
        print(f"- Raw Status: {outcome.raw_status}")
    if outcome.binance_order_id:
        print(f"- Binance Order ID: {outcome.binance_order_id}")
    if outcome.fills:
        print(f"- Executed Qty: {outcome.fills.executed_qty}")
        if outcome.fills.avg_fill_price is not None:
            print(f"- Avg Fill Price: {outcome.fills.avg_fill_price}")
        print(f"- Total Quote Spent: {outcome.fills.total_quote_spent}")
        print(f"- Fills Count: {outcome.fills.fills_count}")
        if outcome.fills.commission_asset and outcome.fills.commission_total is not None:
            print(f"- Commission: {outcome.fills.commission_total} {outcome.fills.commission_asset}")
        elif outcome.fills.commission_asset:
            print(f"- Commission: {outcome.fills.commission_asset} (see audit for breakdown)")
    print(f"- Message: {outcome.message}")
    return 0 if outcome.local_status in ("filled", "submitted", "partially_filled") else 2


def cmd_trade_executions_list(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        rows = StateManager(conn).list_executions(limit=int(getattr(args, "limit", 20)))
    if not rows:
        print("(no executions)")
        return 0

    def _cell(v: object, width: int) -> str:
        s = "" if v is None else str(v)
        if len(s) > width:
            return s[: max(0, width - 1)] + "…"
        return s

    print(f"Executions: {len(rows)}")
    print(
        f"{'EXEC_ID':>7} {'CAND_ID':>7} {'PLAN_ID':>7} {'SYMBOL':<10} {'TYPE':<10} {'ENV':<7} {'STATUS':<18} "
        f"{'QUOTE_QTY':<10} {'LMT_PX':<10} {'EXEC_QTY':<12} {'AVG_PRICE':<14} {'ORDER_ID':<10}"
    )
    for r in rows:
        print(
            f"{int(r['execution_id']):>7} "
            f"{int(r.get('candidate_id') or 0):>7} "
            f"{int(r.get('plan_id') or 0):>7} "
            f"{_cell(r.get('symbol') or '-', 10):<10} "
            f"{_cell(r.get('order_type') or '-', 10):<10} "
            f"{_cell(r.get('execution_environment') or '-', 7):<7} "
            f"{_cell(r.get('local_status') or '-', 18):<18} "
            f"{_cell(r.get('quote_order_qty') or '-', 10):<10} "
            f"{_cell(r.get('limit_price') or '-', 10):<10} "
            f"{_cell(r.get('executed_quantity') or '-', 12):<12} "
            f"{_cell(r.get('avg_fill_price') or '-', 14):<14} "
            f"{_cell(r.get('binance_order_id') or '-', 10):<10} "
        )
    return 0


def cmd_trade_executions_show(args: argparse.Namespace) -> int:
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
    with connect(db_path) as conn:
        row = StateManager(conn).get_execution(execution_id=int(args.execution_id))
    if not row:
        print("(not found)")
        return 2
    for k in [
        "execution_id",
        "candidate_id",
        "plan_id",
        "trade_request_id",
        "symbol",
        "side",
        "order_type",
        "execution_environment",
        "client_order_id",
        "binance_order_id",
        "quote_order_qty",
        "limit_price",
        "time_in_force",
        "requested_quantity",
        "executed_quantity",
        "avg_fill_price",
        "total_quote_spent",
        "commission_total",
        "commission_asset",
        "fills_count",
        "local_status",
        "raw_status",
        "retry_count",
        "submitted_at_utc",
        "reconciled_at_utc",
        "expired_at_utc",
        "created_at_utc",
        "updated_at_utc",
    ]:
        print(f"{k}={row.get(k)}")
    return 0


def cmd_trade_execution_cancel(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    from cryptogent.execution.result_parser import parse_fills

    with connect(db_path) as conn:
        state = StateManager(conn)
        row = state.get_execution(execution_id=int(args.execution_id))
        if not row:
            print("(not found)")
            return 2

        if str(row.get("order_type") or "").strip().upper() != "LIMIT_BUY":
            print("Not supported: only LIMIT_BUY executions can be cancelled in MVP.")
            return 2

        if str(row.get("local_status") or "") in ("filled", "cancelled", "expired", "failed", "rejected"):
            print(f"Not cancellable (status={row.get('local_status')})")
            return 2

        symbol = str(row.get("symbol") or "").strip().upper()
        client_order_id = str(row.get("client_order_id") or "").strip()
        if not (symbol and client_order_id):
            print("Missing symbol/client_order_id")
            return 2

        try:
            client.cancel_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
        except BinanceAPIError as e:
            state.append_audit(
                level="ERROR",
                event="order_cancel_failed",
                details={"execution_id": int(args.execution_id), "symbol": symbol, "client_order_id": client_order_id, "error": str(e)},
            )
            print(f"ERROR: {e}")
            return 2

        # Reconcile immediately to reflect exchange truth.
        try:
            order = client.get_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
            raw_status = str(order.get("status") or "") or None
            order_id = str(order.get("orderId") or "") or None
            fills = None
            try:
                fills = parse_fills(order)
            except Exception:
                fills = None

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
                execution_id=int(args.execution_id),
                local_status=local_status,
                raw_status=raw_status,
                binance_order_id=order_id,
                executed_quantity=str(fills.executed_qty) if fills else None,
                avg_fill_price=str(fills.avg_fill_price) if fills and fills.avg_fill_price is not None else None,
                total_quote_spent=str(fills.total_quote_spent) if fills else None,
                commission_total=str(fills.commission_total) if fills and fills.commission_total is not None else None,
                commission_asset=(fills.commission_asset if fills else None),
                fills_count=(fills.fills_count if fills else None),
                retry_count=int(row.get("retry_count") or 0),
                message="cancel_requested",
                details_json=None,
                submitted_at_utc=str(row.get("submitted_at_utc") or "") or None,
                reconciled_at_utc=utcnow_iso(),
            )
        except BinanceAPIError:
            # Best-effort: cancel request succeeded but reconciliation failed.
            pass

    print("Cancelled (requested)")
    return 0


def cmd_trade_reconcile(args: argparse.Namespace) -> int:
    client = _client_from_args(args)
    paths = ConfigPaths.from_cli(config_path=args.config, db_path=args.db)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)

    runtime_env = "testnet" if cfg.binance_testnet else "mainnet"
    timeout_min = int(getattr(args, "limit_order_timeout_minutes", 30))
    auto_cancel = getattr(args, "auto_cancel_expired", None)
    if auto_cancel is None:
        auto_cancel = bool(cfg.trading_auto_cancel_expired_limit_orders)
    limit = int(getattr(args, "limit", 50))

    from cryptogent.execution.result_parser import parse_fills

    def _parse_iso(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)

    updated = 0
    expired = 0
    skipped = 0
    errors = 0

    with connect(db_path) as conn:
        state = StateManager(conn)
        rows = state.list_reconcilable_executions(limit=limit)
        if not rows:
            print("(no executions to reconcile)")
            return 0

        now = datetime.now(UTC)
        for r in rows:
            exec_id = int(r["execution_id"])
            symbol = str(r.get("symbol") or "")
            client_order_id = str(r.get("client_order_id") or "")
            exec_env = str(r.get("execution_environment") or "").strip().lower()
            order_type = str(r.get("order_type") or "").strip().upper()

            if exec_env and exec_env != runtime_env:
                skipped += 1
                state.append_audit(
                    level="WARN",
                    event="reconcile_skipped_env_mismatch",
                    details={"execution_id": exec_id, "execution_environment": exec_env, "runtime_environment": runtime_env},
                )
                continue

            # Timeout enforcement for LIMIT_BUY (local expire only).
            submitted_at = r.get("submitted_at_utc")
            if order_type == "LIMIT_BUY" and submitted_at:
                try:
                    age = now - _parse_iso(str(submitted_at))
                    if age.total_seconds() >= timeout_min * 60:
                        if auto_cancel:
                            try:
                                client.cancel_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
                                state.append_audit(
                                    level="WARN",
                                    event="limit_order_cancel_requested",
                                    details={"execution_id": exec_id, "client_order_id": client_order_id, "reason": "timeout"},
                                )
                            except BinanceAPIError as e:
                                state.append_audit(
                                    level="ERROR",
                                    event="limit_order_cancel_failed",
                                    details={"execution_id": exec_id, "error": str(e), "reason": "timeout"},
                                )
                            # Always mark local expired_at_utc; reconciliation below may update status to cancelled/filled.
                            state.update_execution(
                                execution_id=exec_id,
                                local_status=str(r.get("local_status") or "open"),
                                raw_status=str(r.get("raw_status") or "") or None,
                                binance_order_id=None,
                                executed_quantity=None,
                                avg_fill_price=None,
                                total_quote_spent=None,
                                commission_total=None,
                                commission_asset=None,
                                fills_count=None,
                                retry_count=int(r.get("retry_count") or 0),
                                message=f"limit_order_timeout_reached:{timeout_min}m; cancel_attempted",
                                details_json=None,
                                submitted_at_utc=str(r.get("submitted_at_utc") or "") or None,
                                reconciled_at_utc=utcnow_iso(),
                                expired_at_utc=utcnow_iso(),
                            )
                        else:
                            state.mark_execution_expired(execution_id=exec_id, reason=f"limit_order_timeout_reached:{timeout_min}m")
                            expired += 1
                            continue
                except Exception:
                    # If we can't parse time, fail closed by not expiring; reconciliation still runs.
                    pass

            try:
                order = client.get_order_by_client_order_id(symbol=symbol, client_order_id=client_order_id)
            except BinanceAPIError as e:
                errors += 1
                state.append_audit(level="ERROR", event="reconcile_failed", details={"execution_id": exec_id, "error": str(e)})
                continue

            raw_status = str(order.get("status") or "") or None
            order_id = str(order.get("orderId") or "") or None
            fills = None
            try:
                fills = parse_fills(order)
            except Exception:
                fills = None

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
                execution_id=exec_id,
                local_status=local_status,
                raw_status=raw_status,
                binance_order_id=order_id,
                executed_quantity=str(fills.executed_qty) if fills else None,
                avg_fill_price=str(fills.avg_fill_price) if fills and fills.avg_fill_price is not None else None,
                total_quote_spent=str(fills.total_quote_spent) if fills else None,
                commission_total=str(fills.commission_total) if fills and fills.commission_total is not None else None,
                commission_asset=(fills.commission_asset if fills else None),
                fills_count=(fills.fills_count if fills else None),
                retry_count=int(r.get("retry_count") or 0),
                message="reconciled",
                details_json=None,
                submitted_at_utc=str(r.get("submitted_at_utc") or "") or None,
                reconciled_at_utc=utcnow_iso(),
            )
            updated += 1

    print(f"OK reconciled updated={updated} expired={expired} skipped={skipped} errors={errors}")
    return 0 if errors == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cryptogent", description="CryptoGent CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create default config and initialize DB.")
    _add_common_paths(p_init)
    p_init.set_defaults(fn=cmd_init)

    p_cfg = sub.add_parser("config", help="Show effective configuration.")
    _add_common_paths(p_cfg)
    p_cfg.set_defaults(fn=cmd_config_show)
    cfg_sub = p_cfg.add_subparsers(dest="config_cmd", required=False)

    p_cfg_show = cfg_sub.add_parser("show", help="Show effective configuration.")
    _add_common_paths(p_cfg_show)
    p_cfg_show.set_defaults(fn=cmd_config_show)

    p_cfg_set = cfg_sub.add_parser("set-binance", help="Store Binance API key/secret in config TOML.")
    _add_common_paths(p_cfg_set)
    p_cfg_set.add_argument("--api-key", type=str, default="", help="Binance API key (stored in plaintext).")
    p_cfg_set.add_argument(
        "--api-secret",
        type=str,
        default=None,
        help="Binance API secret (stored in plaintext; prefer --api-secret-stdin).",
    )
    p_cfg_set.add_argument(
        "--api-secret-stdin",
        action="store_true",
        help="Read API secret from stdin (avoids shell history).",
    )
    p_cfg_set.set_defaults(fn=cmd_config_set_binance)

    p_cfg_use_testnet = cfg_sub.add_parser("use-testnet", help="Toggle Binance to Spot Test Network via config flag.")
    _add_common_paths(p_cfg_use_testnet)
    p_cfg_use_testnet.set_defaults(fn=cmd_config_use_testnet)

    p_cfg_use_mainnet = cfg_sub.add_parser("use-mainnet", help="Toggle Binance back to real Spot API via config flag.")
    _add_common_paths(p_cfg_use_mainnet)
    p_cfg_use_mainnet.set_defaults(fn=cmd_config_use_mainnet)

    p_cfg_set_testnet = cfg_sub.add_parser("set-binance-testnet", help="Store Binance testnet API key/secret in config.")
    _add_common_paths(p_cfg_set_testnet)
    p_cfg_set_testnet.add_argument("--api-key", type=str, default="", help="Binance testnet API key (plaintext).")
    p_cfg_set_testnet.add_argument(
        "--api-secret",
        type=str,
        default=None,
        help="Binance testnet API secret (plaintext; prefer --api-secret-stdin).",
    )
    p_cfg_set_testnet.add_argument(
        "--api-secret-stdin",
        action="store_true",
        help="Read API secret from stdin (avoids shell history).",
    )
    p_cfg_set_testnet.set_defaults(fn=cmd_config_set_binance_testnet)

    p_status = sub.add_parser("status", help="Show local setup status.")
    _add_common_paths(p_status)
    p_status.set_defaults(fn=cmd_status)

    p_ex = sub.add_parser("exchange", help="Binance Spot connectivity utilities (no trading).")
    _add_common_paths(p_ex)
    ex_sub = p_ex.add_subparsers(dest="exchange_cmd", required=True)

    p_ex_ping = ex_sub.add_parser("ping", help="Call /api/v3/ping.")
    _add_common_paths(p_ex_ping)
    _add_exchange_tls_args(p_ex_ping)
    p_ex_ping.set_defaults(fn=cmd_exchange_ping)

    p_ex_time = ex_sub.add_parser("time", help="Call /api/v3/time.")
    _add_common_paths(p_ex_time)
    _add_exchange_tls_args(p_ex_time)
    p_ex_time.set_defaults(fn=cmd_exchange_time)

    p_ex_info = ex_sub.add_parser("info", help="Call /api/v3/exchangeInfo.")
    _add_common_paths(p_ex_info)
    _add_exchange_tls_args(p_ex_info)
    p_ex_info.add_argument("--symbol", type=str, default=None, help="Optional symbol (e.g. BTCUSDT).")
    p_ex_info.set_defaults(fn=cmd_exchange_info)

    p_ex_bal = ex_sub.add_parser("balances", help="Call /api/v3/account and print balances (requires key+secret).")
    _add_common_paths(p_ex_bal)
    _add_exchange_tls_args(p_ex_bal)
    p_ex_bal.add_argument("--all", action="store_true", help="Show zero balances too.")
    p_ex_bal.set_defaults(fn=cmd_exchange_balances)

    p_sync = sub.add_parser("sync", help="Sync exchange state into the local SQLite cache (no trading).")
    _add_common_paths(p_sync)
    _add_exchange_tls_args(p_sync)
    sync_sub = p_sync.add_subparsers(dest="sync_cmd", required=True)

    p_sync_startup = sync_sub.add_parser("startup", help="Startup sync: account snapshot + balances + open orders.")
    _add_common_paths(p_sync_startup)
    _add_exchange_tls_args(p_sync_startup)
    p_sync_startup.set_defaults(fn=cmd_sync_startup)

    p_sync_bal = sync_sub.add_parser("balances", help="Sync balances into the local cache.")
    _add_common_paths(p_sync_bal)
    _add_exchange_tls_args(p_sync_bal)
    p_sync_bal.set_defaults(fn=cmd_sync_balances)

    p_sync_oo = sync_sub.add_parser("open-orders", help="Sync open orders into the local cache.")
    _add_common_paths(p_sync_oo)
    _add_exchange_tls_args(p_sync_oo)
    p_sync_oo.add_argument("--symbol", type=str, default=None, help="Optional symbol (e.g. BTCUSDT).")
    p_sync_oo.set_defaults(fn=cmd_sync_open_orders)

    p_show = sub.add_parser("show", help="Show cached state from SQLite (no network).")
    _add_common_paths(p_show)
    show_sub = p_show.add_subparsers(dest="show_cmd", required=True)

    p_show_bal = show_sub.add_parser("balances", help="Show cached balances.")
    _add_common_paths(p_show_bal)
    p_show_bal.add_argument("--all", action="store_true", help="Include zero balances.")
    p_show_bal.add_argument("--limit", type=int, default=None, help="Limit rows.")
    p_show_bal.add_argument("--filter", type=str, default=None, help="Filter by asset substring (e.g. USDT).")
    p_show_bal.set_defaults(fn=cmd_show_balances)

    p_show_oo = show_sub.add_parser("open-orders", help="Show cached open orders.")
    _add_common_paths(p_show_oo)
    p_show_oo.add_argument("--symbol", type=str, default=None, help="Optional symbol (e.g. BTCUSDT).")
    p_show_oo.add_argument("--limit", type=int, default=None, help="Limit rows.")
    p_show_oo.set_defaults(fn=cmd_show_open_orders)

    p_show_audit = show_sub.add_parser("audit", help="Show cached audit log entries.")
    _add_common_paths(p_show_audit)
    p_show_audit.add_argument("--limit", type=int, default=50, help="Limit rows (default: 50).")
    p_show_audit.set_defaults(fn=cmd_show_audit)

    p_trade = sub.add_parser("trade", help="Trade request workflow (no execution yet).")
    _add_common_paths(p_trade)
    trade_sub = p_trade.add_subparsers(dest="trade_cmd", required=True)

    p_trade_start = trade_sub.add_parser("start", help="Create a new trade request.")
    _add_common_paths(p_trade_start)
    p_trade_start.add_argument("--profit-target-pct", required=True, help="Profit target percent (e.g. 2.5).")
    p_trade_start.add_argument("--stop-loss-pct", default=None, help="Stop-loss percent (defaults from config).")
    p_trade_start.add_argument(
        "--deadline",
        default=None,
        help="ISO8601 deadline with timezone (e.g. 2026-03-14T12:00:00+00:00).",
    )
    p_trade_start.add_argument(
        "--deadline-minutes",
        type=int,
        default=None,
        help="Relative deadline in minutes from now (alternative to --deadline).",
    )
    p_trade_start.add_argument(
        "--deadline-hours",
        type=int,
        default=None,
        help="Relative deadline in hours from now (alternative to --deadline).",
    )
    p_trade_start.add_argument("--budget-mode", default=None, help="Budget mode: manual|auto (defaults from config).")
    p_trade_start.add_argument("--budget", default=None, help="Budget amount (required for manual mode).")
    p_trade_start.add_argument("--budget-asset", default="USDT", help="Budget asset code (default: USDT).")
    p_trade_start.add_argument("--symbol", default=None, help="Preferred symbol (e.g. BTCUSDT). Optional.")
    p_trade_start.add_argument("--exit-asset", default=None, help="Exit asset (defaults from config).")
    p_trade_start.add_argument("--label", default=None, help="Optional short label.")
    p_trade_start.add_argument("--notes", default=None, help="Optional notes.")
    p_trade_start.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
    p_trade_start.set_defaults(fn=cmd_trade_start)

    p_trade_list = trade_sub.add_parser("list", help="List trade requests.")
    _add_common_paths(p_trade_list)
    p_trade_list.add_argument("--limit", type=int, default=20, help="Limit rows (default: 20).")
    p_trade_list.set_defaults(fn=cmd_trade_list)

    p_trade_show = trade_sub.add_parser("show", help="Show one trade request.")
    _add_common_paths(p_trade_show)
    p_trade_show.add_argument("id", type=int, help="Trade request id.")
    p_trade_show.set_defaults(fn=cmd_trade_show)

    p_trade_cancel = trade_sub.add_parser("cancel", help="Cancel a NEW trade request.")
    _add_common_paths(p_trade_cancel)
    p_trade_cancel.add_argument("id", type=int, help="Trade request id.")
    p_trade_cancel.set_defaults(fn=cmd_trade_cancel)

    p_trade_validate = trade_sub.add_parser("validate", help="Validate a trade request against Binance symbol rules.")
    _add_common_paths(p_trade_validate)
    _add_exchange_tls_args(p_trade_validate)
    p_trade_validate.add_argument("id", type=int, help="Trade request id.")
    p_trade_validate.set_defaults(fn=cmd_trade_validate)

    p_trade_plan = trade_sub.add_parser("plan", help="Trade plan commands (Phase 5; no execution).")
    _add_common_paths(p_trade_plan)
    _add_exchange_tls_args(p_trade_plan)
    plan_sub = p_trade_plan.add_subparsers(dest="plan_cmd", required=True)

    p_trade_plan_build = plan_sub.add_parser("build", help="Build and persist a deterministic trade plan from a trade request.")
    _add_common_paths(p_trade_plan_build)
    _add_exchange_tls_args(p_trade_plan_build)
    p_trade_plan_build.add_argument("id", type=int, help="Trade request id.")
    p_trade_plan_build.add_argument("--candle-interval", default="5m", help="Candle interval (default: 5m).")
    p_trade_plan_build.add_argument("--candle-count", type=int, default=288, help="Number of candles (default: 288 ≈ 24h).")
    p_trade_plan_build.set_defaults(fn=cmd_trade_plan)

    p_trade_plan_list = plan_sub.add_parser("list", help="List trade plans.")
    _add_common_paths(p_trade_plan_list)
    p_trade_plan_list.add_argument("--limit", type=int, default=20, help="Limit rows (default: 20).")
    p_trade_plan_list.set_defaults(fn=cmd_trade_plan_list)

    p_trade_plan_show = plan_sub.add_parser("show", help="Show one trade plan.")
    _add_common_paths(p_trade_plan_show)
    p_trade_plan_show.add_argument("plan_id", type=int, help="Trade plan id.")
    p_trade_plan_show.set_defaults(fn=cmd_trade_plan_show)

    # Backwards-compatible alias for the previous `trade plan <trade_request_id>` form.
    p_trade_plan_build_alias = trade_sub.add_parser("plan-build", help=argparse.SUPPRESS)
    _add_common_paths(p_trade_plan_build_alias)
    _add_exchange_tls_args(p_trade_plan_build_alias)
    p_trade_plan_build_alias.add_argument("id", type=int, help="Trade request id.")
    p_trade_plan_build_alias.add_argument("--candle-interval", default="5m")
    p_trade_plan_build_alias.add_argument("--candle-count", type=int, default=288)
    p_trade_plan_build_alias.set_defaults(fn=cmd_trade_plan)

    p_trade_safety = trade_sub.add_parser("safety", help="Phase 6 safety validation (plan-based; no execution).")
    _add_common_paths(p_trade_safety)
    _add_exchange_tls_args(p_trade_safety)
    p_trade_safety.add_argument("plan_id", type=int, help="Trade plan id.")
    p_trade_safety.add_argument("--max-age-minutes", type=int, default=60, help="Expire plans older than this (default: 60).")
    p_trade_safety.add_argument("--price-drift-warn-pct", default="1.0", help="Warning threshold for price drift percent (default: 1.0).")
    p_trade_safety.add_argument("--price-drift-unsafe-pct", default="3.0", help="Unsafe threshold for price drift percent (default: 3.0).")
    p_trade_safety.add_argument("--max-position-pct", default="25", help="Max approved budget as percent of free quote balance (default: 25).")
    p_trade_safety.add_argument("--max-stop-loss-pct", default="10", help="Reject stop-loss > this percent (default: 10).")
    p_trade_safety.add_argument(
        "--order-type",
        default="MARKET_BUY",
        help="Order type for the generated execution candidate: MARKET_BUY|LIMIT_BUY (default: MARKET_BUY).",
    )
    p_trade_safety.add_argument(
        "--limit-price",
        default=None,
        help="Required when --order-type=LIMIT_BUY. Limit price in quote asset (e.g. 61829.72).",
    )
    p_trade_safety.set_defaults(fn=cmd_trade_safety)

    p_trade_execute = trade_sub.add_parser("execute", help="Phase 7 execution (BUY MARKET only; candidate-based).")
    _add_common_paths(p_trade_execute)
    _add_exchange_tls_args(p_trade_execute)
    p_trade_execute.add_argument("candidate_id", type=int, help="Execution candidate id.")
    p_trade_execute.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
    p_trade_execute.set_defaults(fn=cmd_trade_execute)

    p_trade_exec = trade_sub.add_parser("execution", help="Inspect stored Phase 7 execution attempts.")
    _add_common_paths(p_trade_exec)
    exec_sub = p_trade_exec.add_subparsers(dest="exec_cmd", required=True)

    p_trade_exec_list = exec_sub.add_parser("list", help="List stored executions.")
    _add_common_paths(p_trade_exec_list)
    p_trade_exec_list.add_argument("--limit", type=int, default=20, help="Limit rows (default: 20).")
    p_trade_exec_list.set_defaults(fn=cmd_trade_executions_list)

    p_trade_exec_show = exec_sub.add_parser("show", help="Show one execution.")
    _add_common_paths(p_trade_exec_show)
    p_trade_exec_show.add_argument("execution_id", type=int, help="Execution id.")
    p_trade_exec_show.set_defaults(fn=cmd_trade_executions_show)

    p_trade_exec_cancel = exec_sub.add_parser("cancel", help="Cancel an open LIMIT_BUY execution on Binance.")
    _add_common_paths(p_trade_exec_cancel)
    _add_exchange_tls_args(p_trade_exec_cancel)
    p_trade_exec_cancel.add_argument("execution_id", type=int, help="Execution id.")
    p_trade_exec_cancel.set_defaults(fn=cmd_trade_execution_cancel)

    p_trade_reconcile = trade_sub.add_parser("reconcile", help="Reconcile executions with Binance (supports LIMIT timeout expiry).")
    _add_common_paths(p_trade_reconcile)
    _add_exchange_tls_args(p_trade_reconcile)
    p_trade_reconcile.add_argument("--limit", type=int, default=50, help="Limit executions checked (default: 50).")
    p_trade_reconcile.add_argument(
        "--limit-order-timeout-minutes",
        type=int,
        default=30,
        help="Mark open LIMIT_BUY executions as expired after this many minutes (default: 30).",
    )
    p_trade_reconcile.add_argument(
        "--auto-cancel-expired",
        action="store_true",
        default=None,
        help="Cancel expired LIMIT_BUY orders on Binance (default from config: trading.auto_cancel_expired_limit_orders).",
    )
    p_trade_reconcile.set_defaults(fn=cmd_trade_reconcile)

    p_menu = sub.add_parser("menu", help="Interactive menu wrapper over subcommands.")
    _add_common_paths(p_menu)
    p_menu.set_defaults(fn=cmd_menu)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Best-effort lifecycle metadata for Phase 3 recovery readiness.
    if hasattr(args, "config") and hasattr(args, "db"):
        paths = ConfigPaths.from_cli(config_path=getattr(args, "config"), db_path=getattr(args, "db"))
        config_path = ensure_default_config(paths.config_path)
        db_path = ensure_db_initialized(config_path=config_path, db_path=paths.db_path)
        cfg = load_config(config_path)
        mode = "TESTNET" if cfg.binance_testnet else "MAINNET"
        try:
            with connect(db_path) as conn:
                StateManager(conn).update_system_start(current_mode=mode)
        except Exception:
            pass

        def _shutdown_hook() -> None:
            try:
                with connect(db_path) as conn:
                    StateManager(conn).update_system_shutdown()
            except Exception:
                return

        import atexit

        atexit.register(_shutdown_hook)

    return int(args.fn(args))
