"""Technical indicators for scalping and swing signals."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Bar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    timestamp: str

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self) -> float:
        if self.mid <= 0:
            return 0.0
        return ((self.ask - self.bid) / self.mid) * 100


@dataclass
class IndicatorState:
    bars: deque[Bar] = field(default_factory=lambda: deque(maxlen=400))
    cumulative_pv: float = 0.0
    cumulative_volume: float = 0.0
    prev_day_close: float = 0.0  # set by BarManager after warmup

    def add_bar(self, bar: Bar) -> None:
        self.bars.append(bar)
        typical_price = (bar.high + bar.low + bar.close) / 3
        self.cumulative_pv += typical_price * bar.volume
        self.cumulative_volume += bar.volume

    def vwap(self) -> float | None:
        if self.cumulative_volume <= 0:
            return None
        return self.cumulative_pv / self.cumulative_volume

    def rsi(self, period: int = 14) -> float | None:
        if len(self.bars) < period + 1:
            return None
        closes = [b.close for b in self.bars]
        gains: list[float] = []
        losses: list[float] = []
        for i in range(-period, 0):
            delta = closes[i] - closes[i - 1]
            if delta >= 0:
                gains.append(delta)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(delta))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def ema(self, period: int) -> float | None:
        """Exponential moving average over the last `period` bars."""
        bars = list(self.bars)
        if len(bars) < period:
            return None
        closes = [b.close for b in bars]
        k = 2.0 / (period + 1)
        ema_val = sum(closes[:period]) / period
        for price in closes[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    def atr(self, period: int = 14) -> float | None:
        """Average True Range — measures volatility."""
        bars = list(self.bars)
        if len(bars) < period + 1:
            return None
        true_ranges: list[float] = []
        for i in range(1, len(bars)):
            high = bars[i].high
            low = bars[i].low
            prev_close = bars[i - 1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        recent_trs = true_ranges[-period:]
        return sum(recent_trs) / len(recent_trs)

    def avg_volume(self, lookback: int = 20) -> float | None:
        if len(self.bars) < lookback:
            return None
        recent = list(self.bars)[-lookback:]
        return sum(b.volume for b in recent) / lookback

    def latest_close(self) -> float | None:
        if not self.bars:
            return None
        return self.bars[-1].close

    def latest_high(self) -> float | None:
        if not self.bars:
            return None
        return self.bars[-1].high

    def vwap_deviation_pct(self) -> float | None:
        vwap = self.vwap()
        close = self.latest_close()
        if vwap is None or close is None or vwap == 0:
            return None
        return ((close - vwap) / vwap) * 100

    def gap_pct_from_prev_close(self) -> float | None:
        """Gap of current price vs previous day close (requires prev_day_close set)."""
        close = self.latest_close()
        if not close or not self.prev_day_close:
            return None
        return ((close - self.prev_day_close) / self.prev_day_close) * 100
