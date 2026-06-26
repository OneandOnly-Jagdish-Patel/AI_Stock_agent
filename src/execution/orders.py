"""Alpaca order execution."""

from __future__ import annotations

import logging
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from src.config import AppConfig, StrategyConfig

logger = logging.getLogger(__name__)


class OrderExecutor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = TradingClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper="paper" in config.alpaca_base_url,
        )

    def get_account(self) -> Any:
        return self.client.get_account()

    def get_equity(self) -> float:
        account = self.get_account()
        return float(account.equity)

    def get_buying_power(self) -> float:
        account = self.get_account()
        return float(account.buying_power)

    @staticmethod
    def _bracket_prices(ref_price: float, strategy: StrategyConfig) -> tuple[float, float]:
        take_profit = round(ref_price * (1 + strategy.take_profit_pct / 100), 2)
        stop_loss = round(ref_price * (1 - strategy.stop_loss_pct / 100), 2)
        return take_profit, stop_loss

    def submit_market_buy(self, symbol: str, qty: float) -> Any:
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(request)
        logger.info("Submitted market BUY %s x %s -> %s", qty, symbol, order.id)
        return order

    def submit_bracket_buy(
        self,
        symbol: str,
        qty: float,
        ref_price: float,
        take_profit_pct: float | None = None,
    ) -> Any:
        tp_pct = take_profit_pct if take_profit_pct is not None else self.config.strategy.take_profit_pct
        take_profit = round(ref_price * (1 + tp_pct / 100), 2)
        stop_loss = round(ref_price * (1 - self.config.strategy.stop_loss_pct / 100), 2)
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=take_profit),
            stop_loss=StopLossRequest(stop_price=stop_loss),
        )
        order = self.client.submit_order(request)
        logger.info(
            "Submitted bracket BUY %s x %s @ ~%.2f (TP=%.2f SL=%.2f) -> %s",
            qty,
            symbol,
            ref_price,
            take_profit,
            stop_loss,
            order.id,
        )
        return order

    def submit_limit_sell(self, symbol: str, qty: float, limit_price: float) -> Any:
        request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=round(limit_price, 2),
        )
        order = self.client.submit_order(request)
        logger.info("Submitted limit SELL %s x %s @ %.2f -> %s", qty, symbol, limit_price, order.id)
        return order

    def submit_market_sell(self, symbol: str, qty: float) -> Any:
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(request)
        logger.info("Submitted market SELL %s x %s -> %s", qty, symbol, order.id)
        return order

    def cancel_open_orders(self, symbol: str) -> int:
        from alpaca.trading.requests import GetOrdersRequest

        request = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[symbol],
        )
        orders = self.client.get_orders(request)
        cancelled = 0
        for order in orders:
            self.client.cancel_order_by_id(order.id)
            cancelled += 1
            logger.info("Cancelled open order %s for %s", order.id, symbol)
        return cancelled

    def cancel_order(self, order_id: str) -> None:
        self.client.cancel_order_by_id(order_id)

    def get_order(self, order_id: str) -> Any:
        return self.client.get_order_by_id(order_id)
