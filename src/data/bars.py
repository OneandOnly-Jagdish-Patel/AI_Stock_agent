"""Historical bar fetching and warmup for indicators."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.config import AppConfig
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

    def warmup(self, symbols: list[str] | None = None) -> None:
        target = symbols or self.symbols
        if not target:
            return
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=2)
        request = StockBarsRequest(
            symbol_or_symbols=target,
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            feed=_parse_feed(self.config.alpaca_data_feed),
        )
        try:
            bars = self._data_client.get_stock_bars(request)
        except Exception:
            logger.exception("Failed to fetch historical bars for warmup")
            return

        today = date.today()
        for symbol in target:
            if symbol not in bars.data:
                continue
            state = self.states.setdefault(symbol, IndicatorState())
            prev_day_close: float = 0.0
            for b in bars.data[symbol]:
                bar = Bar(
                    timestamp=str(b.timestamp),
                    open=float(b.open),
                    high=float(b.high),
                    low=float(b.low),
                    close=float(b.close),
                    volume=float(b.volume),
                )
                # Track the last bar from any day before today as prev_day_close
                bar_date = b.timestamp.date() if hasattr(b.timestamp, "date") else today
                if bar_date < today:
                    prev_day_close = float(b.close)
                state.add_bar(bar)
            if prev_day_close > 0:
                state.prev_day_close = prev_day_close
            logger.info(
                "Warmed up %s with %d bars (prev_day_close=%.2f)",
                symbol,
                len(state.bars),
                state.prev_day_close,
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
