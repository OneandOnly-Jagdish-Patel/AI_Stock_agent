"""Position sizing based on equity risk."""

from __future__ import annotations

import math

from src.config import RiskConfig, StrategyConfig


def calculate_position_size(
    equity: float,
    entry_price: float,
    risk_config: RiskConfig,
    strategy_config: StrategyConfig,
) -> float:
    if entry_price <= 0 or equity <= 0:
        return 0.0

    risk_amount = equity * (risk_config.max_risk_per_trade_pct / 100)
    stop_distance = entry_price * (strategy_config.stop_loss_pct / 100)
    if stop_distance <= 0:
        return 0.0

    shares = risk_amount / stop_distance
    max_shares_by_equity = (equity * 0.1) / entry_price
    shares = min(shares, max_shares_by_equity)
    return max(1.0, math.floor(shares))
