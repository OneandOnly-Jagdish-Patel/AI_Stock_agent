"""Entry and exit signal evaluation rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config import ExecutionConfig, StrategyConfig
from src.strategy.indicators import IndicatorState, Quote


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    signal_type: SignalType
    reason: str
    context: dict


def evaluate_entry(
    symbol: str,
    state: IndicatorState,
    quote: Quote | None,
    config: StrategyConfig,
    execution: ExecutionConfig | None = None,
) -> Signal:
    rsi = state.rsi(config.rsi_period)
    vwap_dev = state.vwap_deviation_pct()
    avg_vol = state.avg_volume()
    latest = state.bars[-1] if state.bars else None
    max_spread = execution.max_spread_pct if execution else 0.05

    if rsi is None or vwap_dev is None or avg_vol is None or latest is None:
        return Signal(SignalType.HOLD, "insufficient_data", {})

    if quote is None:
        return Signal(SignalType.HOLD, "no_quote", {"symbol": symbol})

    volume_ratio = latest.volume / avg_vol if avg_vol > 0 else 0
    spread_ok = quote.spread_pct < max_spread

    context = {
        "symbol": symbol,
        "rsi": round(rsi, 2),
        "vwap_deviation_pct": round(vwap_dev, 4),
        "volume_ratio": round(volume_ratio, 2),
        "close": latest.close,
        "spread_pct": round(quote.spread_pct, 4),
        "max_spread_pct": max_spread,
    }

    if not spread_ok:
        return Signal(SignalType.HOLD, "spread_too_wide", context)

    oversold_bounce = (
        rsi <= config.rsi_oversold
        and vwap_dev <= -config.vwap_deviation_pct
        and volume_ratio >= config.volume_spike_ratio
    )

    if oversold_bounce:
        return Signal(
            SignalType.BUY,
            "vwap_rsi_volume_bounce",
            context,
        )

    return Signal(SignalType.HOLD, "no_entry", context)


def evaluate_exit(
    entry_price: float,
    current_price: float,
    highest_since_entry: float,
    config: StrategyConfig,
    rsi: float | None = None,
) -> Signal:
    if entry_price <= 0:
        return Signal(SignalType.HOLD, "invalid_entry", {})

    pnl_pct = ((current_price - entry_price) / entry_price) * 100
    drawdown_from_high = ((current_price - highest_since_entry) / highest_since_entry) * 100

    context = {
        "entry_price": entry_price,
        "current_price": current_price,
        "pnl_pct": round(pnl_pct, 4),
        "drawdown_from_high_pct": round(drawdown_from_high, 4),
        "rsi": round(rsi, 2) if rsi is not None else None,
    }

    if pnl_pct <= -config.stop_loss_pct:
        return Signal(SignalType.SELL, "stop_loss", context)

    if pnl_pct >= config.take_profit_pct:
        return Signal(SignalType.SELL, "take_profit", context)

    if drawdown_from_high <= -config.trailing_stop_pct and pnl_pct > 0:
        return Signal(SignalType.SELL, "trailing_stop", context)

    if rsi is not None and rsi >= config.rsi_overbought and pnl_pct > 0:
        return Signal(SignalType.SELL, "rsi_overbought", context)

    return Signal(SignalType.HOLD, "hold_position", context)
