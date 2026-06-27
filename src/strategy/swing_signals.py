"""Momentum-based entry and exit signals for swing trading mode.

Entry philosophy: trend-following / momentum breakout.
  - Price must be ABOVE the intraday VWAP (confirming uptrend)
  - EMA fast > EMA slow (short-term momentum aligned)
  - Volume spike to confirm institutional interest
  - Stock gapped up from previous close (catalyst / strength)
  - RSI not overbought — avoid chasing extended moves

Exit philosophy: wide trailing stop + AI daily review.
  - Hard stop at -hard_stop_pct% (no exceptions)
  - Trailing stop from session/all-time high once in profit
  - AI morning review decides hold / trail / exit
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config import ExecutionConfig, SwingConfig
from src.strategy.indicators import IndicatorState, Quote


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class SwingSignal:
    signal_type: SignalType
    reason: str
    context: dict


def evaluate_swing_entry(
    symbol: str,
    state: IndicatorState,
    quote: Quote | None,
    swing: SwingConfig,
    execution: ExecutionConfig | None = None,
) -> SwingSignal:
    """Return BUY when momentum breakout criteria are all met."""
    max_spread = execution.max_spread_pct if execution else 0.05
    ema_fast = state.ema(swing.entry_ema_fast)
    ema_slow = state.ema(swing.entry_ema_slow)
    rsi = state.rsi(14)
    vwap_dev = state.vwap_deviation_pct()
    avg_vol = state.avg_volume()
    latest = state.bars[-1] if state.bars else None
    gap_pct = state.gap_pct_from_prev_close()

    context: dict = {
        "symbol": symbol,
        "ema_fast": round(ema_fast, 3) if ema_fast else None,
        "ema_slow": round(ema_slow, 3) if ema_slow else None,
        "rsi": round(rsi, 2) if rsi else None,
        "vwap_deviation_pct": round(vwap_dev, 4) if vwap_dev is not None else None,
        "gap_pct": round(gap_pct, 3) if gap_pct is not None else None,
        "spread_pct": round(quote.spread_pct, 4) if quote else None,
    }

    if any(v is None for v in (ema_fast, ema_slow, rsi, vwap_dev, avg_vol, latest)):
        return SwingSignal(SignalType.HOLD, "insufficient_data", context)

    if quote is None:
        return SwingSignal(SignalType.HOLD, "no_quote", context)

    volume_ratio = latest.volume / avg_vol if avg_vol > 0 else 0
    context["volume_ratio"] = round(volume_ratio, 2)

    if quote.spread_pct > max_spread:
        return SwingSignal(SignalType.HOLD, "spread_too_wide", context)

    # EMA alignment: fast > slow confirms uptrend
    if ema_fast <= ema_slow:  # type: ignore[operator]
        return SwingSignal(SignalType.HOLD, "ema_bearish_alignment", context)

    # Price above VWAP (trend confirmation)
    if vwap_dev < 0:  # type: ignore[operator]
        return SwingSignal(SignalType.HOLD, "price_below_vwap", context)

    # Volume spike needed
    if volume_ratio < swing.entry_min_volume_ratio:
        return SwingSignal(SignalType.HOLD, "volume_too_low", context)

    # RSI must not be overbought
    if rsi > swing.entry_max_rsi:  # type: ignore[operator]
        return SwingSignal(SignalType.HOLD, "rsi_overbought", context)

    # Gap from previous close (if available) — confirms momentum catalyst
    if gap_pct is not None:
        if gap_pct < swing.entry_min_gap_pct:
            return SwingSignal(SignalType.HOLD, "gap_too_small", context)
        if gap_pct > swing.entry_max_gap_pct:
            return SwingSignal(SignalType.HOLD, "gap_too_large_gap_and_crap_risk", context)

    return SwingSignal(SignalType.BUY, "momentum_breakout", context)


def evaluate_swing_exit(
    entry_price: float,
    current_price: float,
    highest_since_entry: float,
    dynamic_stop_pct: float,
    swing: SwingConfig,
    rsi: float | None = None,
) -> SwingSignal:
    """Check hard stop and trailing stop. AI handles target exits."""
    if entry_price <= 0:
        return SwingSignal(SignalType.HOLD, "invalid_entry", {})

    pnl_pct = ((current_price - entry_price) / entry_price) * 100
    drawdown_from_high = ((current_price - highest_since_entry) / highest_since_entry) * 100

    context = {
        "entry_price": entry_price,
        "current_price": current_price,
        "pnl_pct": round(pnl_pct, 4),
        "drawdown_from_high_pct": round(drawdown_from_high, 4),
        "dynamic_stop_pct": round(dynamic_stop_pct, 3),
        "rsi": round(rsi, 2) if rsi is not None else None,
    }

    # Hard stop: absolute floor — never overridden
    if pnl_pct <= -swing.hard_stop_pct:
        return SwingSignal(SignalType.SELL, "hard_stop", context)

    # Dynamic stop (can be tightened by AI review)
    if pnl_pct <= -dynamic_stop_pct:
        return SwingSignal(SignalType.SELL, "dynamic_stop", context)

    # Trailing stop: activate only after profit_lock_pct is reached
    in_profit_enough = pnl_pct >= swing.profit_lock_pct
    trailing_triggered = drawdown_from_high <= -dynamic_stop_pct and in_profit_enough
    if trailing_triggered:
        return SwingSignal(SignalType.SELL, "trailing_stop", context)

    return SwingSignal(SignalType.HOLD, "hold_position", context)
