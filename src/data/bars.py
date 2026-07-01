"""Historical bar fetching and warmup for indicators."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.config import AppConfig
from src.data.yahoo_client import fetch_intraday_bars, prev_day_close_from_bars
from src.strategy.indicators import Bar, IndicatorState

logger = logging.getLogger(__name__)


def _parse_feed(feed: str) -> DataFeed:
    feed_upper = feed.upper()
    return DataFeed[feed_upper] if feed_upper in DataFeed.__members__ else DataFeed.IEX


class BarManager:
    def __init__(self, config: AppConfig, symbols: list[str] | None = None) -> None:
        self.config = config
        self.symbols = symbols or list(config.symbols)
        self.states: dict[str, IndicatorState] = {s: IndicatorState() for s in self.symbols}
        self._data_client = StockHistoricalDataClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
        )

    def set_symbols(self, symbols: list[str]) -> None:
        self.symbols = symbols
        for s in symbols:
            self.states.setdefault(s, IndicatorState())

    def _warmup_symbol_from_alpaca(self, symbol: str, today: date) -> tuple[int, float]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=2)
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            feed=_parse_feed(self.config.alpaca_data_feed),
        )
        try:
            bars = self._data_client.get_stock_bars(request)
        except Exception:
            logger.debug("Alpaca warmup failed for %s", symbol, exc_info=True)
            return 0, 0.0

        if symbol not in bars.data:
            return 0, 0.0

        state = self.states.setdefault(symbol, IndicatorState())
        prev_day_close = 0.0
        for b in bars.data[symbol]:
            bar = Bar(
                timestamp=str(b.timestamp),
                open=float(b.open),
                high=float(b.high),
                low=float(b.low),
                close=float(b.close),
                volume=float(b.volume),
            )
            bar_date = b.timestamp.date() if hasattr(b.timestamp, "date") else today
            if bar_date < today:
                prev_day_close = float(b.close)
            state.add_bar(bar)
        return len(state.bars), prev_day_close

    def _warmup_symbol_from_yahoo(self, symbol: str, today: date) -> tuple[int, float]:
        try:
            yahoo_bars = fetch_intraday_bars([symbol], period="2d", interval="1m")
        except Exception:
            logger.debug("Yahoo warmup failed for %s", symbol, exc_info=True)
            return 0, 0.0

        raw = yahoo_bars.get(symbol, [])
        if not raw:
            return 0, 0.0

        state = self.states.setdefault(symbol, IndicatorState())
        state.bars.clear()
        state.cumulative_pv = 0.0
        state.cumulative_volume = 0.0
        for b in raw:
            state.add_bar(
                Bar(
                    timestamp=b.timestamp,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume,
                )
            )
        return len(state.bars), prev_day_close_from_bars(raw, today)

    def warmup(self, symbols: list[str] | None = None) -> None:
        target = symbols or self.symbols
        if not target:
            return

        today = date.today()
        min_bars = self.config.research.warmup_min_bars
        use_yahoo_fallback = (
            self.config.research.provider == "yahoo" and self.config.research.yahoo_enabled
        )

        for symbol in target:
            bar_count, prev_day_close = self._warmup_symbol_from_alpaca(symbol, today)
            source = "alpaca"

            if use_yahoo_fallback and (bar_count < min_bars or prev_day_close <= 0):
                yahoo_count, yahoo_prev = self._warmup_symbol_from_yahoo(symbol, today)
                if yahoo_count > bar_count:
                    bar_count = yahoo_count
                    prev_day_close = yahoo_prev
                    source = "yahoo_fallback"

            state = self.states.setdefault(symbol, IndicatorState())
            if prev_day_close > 0:
                state.prev_day_close = prev_day_close

            logger.info(
                "Warmed up %s with %d bars (prev_day_close=%.2f, source=%s)",
                symbol,
                bar_count,
                state.prev_day_close,
                source,
            )

    def on_bar(self, symbol: str, bar_data: dict) -> IndicatorState:
        bar = Bar(
            timestamp=str(bar_data.get("t", "")),
            open=float(bar_data["o"]),
            high=float(bar_data["h"]),
            low=float(bar_data["l"]),
            close=float(bar_data["c"]),
            volume=float(bar_data["v"]),
        )
        state = self.states.setdefault(symbol, IndicatorState())
        state.add_bar(bar)
        return state
