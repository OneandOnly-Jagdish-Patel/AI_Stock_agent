"""Position tracking and end-of-day flatten."""

from __future__ import annotations

import logging
from typing import Any

from alpaca.trading.client import TradingClient

from src.config import AppConfig

logger = logging.getLogger(__name__)


class PositionManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = TradingClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper="paper" in config.alpaca_base_url,
        )

    def list_positions(self) -> list[Any]:
        return self.client.get_all_positions()

    def get_position(self, symbol: str) -> Any | None:
        try:
            return self.client.get_open_position(symbol)
        except Exception:
            return None

    def open_position_count(self) -> int:
        return len(self.list_positions())

    def flatten_all(self) -> None:
        positions = self.list_positions()
        for pos in positions:
            logger.info("Flattening position %s qty=%s", pos.symbol, pos.qty)
            self.client.close_position(pos.symbol)

    def flatten_symbol(self, symbol: str) -> None:
        try:
            self.client.close_position(symbol)
            logger.info("Closed position for %s", symbol)
        except Exception:
            logger.debug("No position to close for %s", symbol, exc_info=True)

    def get_position_qty(self, symbol: str) -> float:
        pos = self.get_position(symbol)
        if pos is None:
            return 0.0
        return float(pos.qty)

    def get_position_side(self, symbol: str) -> str | None:
        pos = self.get_position(symbol)
        if pos is None:
            return None
        return "long" if float(pos.qty) > 0 else "short"
