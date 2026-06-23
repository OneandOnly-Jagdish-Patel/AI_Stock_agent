"""Technical indicators for scalping signals."""

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
    bars: deque[Bar] = field(default_factory=lambda: deque(maxlen=200))
    cumulative_pv: float = 0.0
    cumulative_volume: float = 0.0

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

    def avg_volume(self, lookback: int = 20) -> float | None:
        if len(self.bars) < lookback:
            return None
        recent = list(self.bars)[-lookback:]
        return sum(b.volume for b in recent) / lookback

    def latest_close(self) -> float | None:
        if not self.bars:
            return None
        return self.bars[-1].close

    def vwap_deviation_pct(self) -> float | None:
        vwap = self.vwap()
        close = self.latest_close()
        if vwap is None or close is None or vwap == 0:
            return None
        return ((close - vwap) / vwap) * 100
