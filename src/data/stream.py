"""Alpaca WebSocket market data stream."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream

from src.config import AppConfig
from src.data.bars import _parse_feed
from src.strategy.indicators import Quote

logger = logging.getLogger(__name__)

OnBarHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
OnQuoteHandler = Callable[[Quote], Awaitable[None]]


class MarketDataStream:
    def __init__(
        self,
        config: AppConfig,
        symbols: list[str],
        on_bar: OnBarHandler,
        on_quote: OnQuoteHandler | None = None,
    ) -> None:
        self.config = config
        self.symbols = symbols
        self.on_bar = on_bar
        self.on_quote = on_quote
        self._latest_quotes: dict[str, Quote] = {}
        self._stream = StockDataStream(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            feed=_parse_feed(config.alpaca_data_feed),
        )
        for symbol in symbols:
            self._stream.subscribe_bars(self._handle_bar, symbol)
            self._stream.subscribe_quotes(self._handle_quote, symbol)

    def get_quote(self, symbol: str) -> Quote | None:
        return self._latest_quotes.get(symbol)

    async def _handle_bar(self, bar: Any) -> None:
        symbol = bar.symbol
        data = {
            "t": str(bar.timestamp),
            "o": float(bar.open),
            "h": float(bar.high),
            "l": float(bar.low),
            "c": float(bar.close),
            "v": float(bar.volume),
        }
        await self.on_bar(symbol, data)

    async def _handle_quote(self, quote: Any) -> None:
        q = Quote(
            symbol=quote.symbol,
            bid=float(quote.bid_price),
            ask=float(quote.ask_price),
            timestamp=str(quote.timestamp),
        )
        self._latest_quotes[quote.symbol] = q
        if self.on_quote:
            await self.on_quote(q)

    async def run(self) -> None:
        logger.info("Starting market data stream for %s", self.symbols)
        try:
            await self._stream._run_forever()
        except asyncio.CancelledError:
            self.stop()
            raise

    def stop(self) -> None:
        try:
            self._stream.stop()
        except Exception:
            logger.debug("Stream stop raised", exc_info=True)
