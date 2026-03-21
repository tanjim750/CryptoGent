from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    binance_api_key: str | None
    binance_api_secret: str | None
    binance_base_url: str
    binance_testnet: bool
    binance_recv_window_ms: int
    binance_timeout_s: float
    binance_tls_verify: bool
    binance_ca_bundle_path: Path | None
    binance_spot_bnb_burn: bool | None

    trading_default_exit_asset: str
    trading_default_budget_mode: str
    trading_default_stop_loss_pct: str
    trading_auto_cancel_expired_limit_orders: bool
    trading_monitoring_interval_seconds: int | None

    market_volume_window_fast: int
    market_volume_window_slow: int
    market_volume_spike_ratio: float
    market_volume_zscore_threshold: float
    market_volume_buy_ratio: float
    market_volume_sell_ratio: float
    market_volume_depth_limit: int
    market_volume_wall_ratio: float
    market_volume_imbalance_threshold: float
