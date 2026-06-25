"""Alpaca trading stream for order fill updates."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from alpaca.trading.stream import TradingStream

from src.config import AppConfig

logger = logging.getLogger(__name__)

OnOrderUpdate = Callable[[str, dict], Awaitable[None]]


class OrderUpdateStream:
    def __init__(self, config: AppConfig, on_update: OnOrderUpdate) -> None:
        self.config = config
        self.on_update = on_update
        self._stream = TradingStream(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper="paper" in config.alpaca_base_url,
        )
        self._stream.subscribe_trade_updates(self._handle_update)

    async def _handle_update(self, update: object) -> None:
        event = str(getattr(update, "event", ""))
        order = getattr(update, "order", None)
        if order is None:
            return
        data = {
            "order_id": str(order.id),
            "id": str(order.id),
            "symbol": str(order.symbol),
            "side": str(order.side.value if hasattr(order.side, "value") else order.side),
            "filled_qty": float(order.filled_qty or 0),
            "filled_avg_price": float(order.filled_avg_price or 0),
            "qty": float(order.qty or 0),
            "price": float(order.filled_avg_price or 0),
            "status": str(order.status),
        }
        if event.lower() in ("fill", "partial_fill"):
            await self.on_update("fill", data)
        logger.debug("Order update: %s %s", event, data)

    async def run(self) -> None:
        logger.info("Starting trading update stream")
        try:
            await self._stream._run_forever()
        except asyncio.CancelledError:
            self.stop()
            raise

    def stop(self) -> None:
        try:
            self._stream.stop()
        except Exception:
            logger.debug("Trading stream stop raised", exc_info=True)
