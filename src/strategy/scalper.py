"""Per-symbol scalping state machine."""

from __future__ import annotations

import logging
from enum import Enum

from src.config import AppConfig
from src.data.stream import MarketDataStream
from src.execution.orders import OrderExecutor
from src.journal.logger import TradeJournal, TradeRecord
from src.llm.router import LLMRouter
from src.risk.manager import RiskManager
from src.risk.sizing import calculate_position_size
from src.strategy.indicators import IndicatorState
from src.strategy.signals import SignalType, evaluate_entry, evaluate_exit

logger = logging.getLogger(__name__)


class ScalpState(str, Enum):
    IDLE = "idle"
    TO_BUY = "to_buy"
    BUY_SUBMITTED = "buy_submitted"
    IN_POSITION = "in_position"
    TO_SELL = "to_sell"
    SELL_SUBMITTED = "sell_submitted"


class SymbolScalper:
    def __init__(
        self,
        symbol: str,
        config: AppConfig,
        executor: OrderExecutor,
        risk: RiskManager,
        journal: TradeJournal,
        llm: LLMRouter,
        stream: MarketDataStream,
        avoided_symbols: set[str] | None = None,
    ) -> None:
        self.symbol = symbol
        self.config = config
        self.executor = executor
        self.risk = risk
        self.journal = journal
        self.llm = llm
        self.stream = stream
        self.avoided_symbols = avoided_symbols or set()
        self.state = ScalpState.IDLE
        self.entry_price: float = 0.0
        self.highest_since_entry: float = 0.0
        self.position_qty: float = 0.0
        self.buy_order_id: str | None = None
        self.sell_order_id: str | None = None
        self.pending_exit_reason: str = ""
        self.use_bracket = config.execution.use_bracket_orders

    def _indicator_kwargs(self, context: dict) -> dict:
        return {
            "rsi": context.get("rsi"),
            "vwap_dev": context.get("vwap_deviation_pct"),
            "volume_ratio": context.get("volume_ratio"),
        }

    async def on_bar(self, indicator_state: IndicatorState) -> None:
        quote = self.stream.get_quote(self.symbol)
        close = indicator_state.latest_close()
        if close is None:
            return

        if self.state == ScalpState.IN_POSITION:
            self.highest_since_entry = max(self.highest_since_entry, close)
            exit_signal = evaluate_exit(
                self.entry_price,
                close,
                self.highest_since_entry,
                self.config.strategy,
                indicator_state.rsi(self.config.strategy.rsi_period),
            )
            # Bracket orders handle fixed TP/SL on Alpaca; software handles trailing/RSI only
            if self.use_bracket and exit_signal.reason in ("stop_loss", "take_profit"):
                return
            if exit_signal.signal_type == SignalType.SELL:
                self.journal.log_signal(self.symbol, "exit", exit_signal.reason)
                await self._submit_sell(close, exit_signal.reason)
            return

        if self.state not in (ScalpState.IDLE, ScalpState.TO_BUY):
            return

        if self.symbol in self.avoided_symbols:
            logger.debug("%s skipped — on pre-market avoid list", self.symbol)
            return

        entry_signal = evaluate_entry(
            self.symbol,
            indicator_state,
            quote,
            self.config.strategy,
            self.config.execution,
        )

        if entry_signal.signal_type != SignalType.BUY:
            return

        can_trade, reason = self.risk.can_open_position(self.symbol)
        if not can_trade:
            logger.info("%s entry blocked by risk: %s", self.symbol, reason)
            return

        ctx = entry_signal.context
        jc = self.config.journal_context
        if jc.enabled:
            stats = self.journal.get_similar_setup_stats(
                self.symbol,
                ctx.get("rsi", 0),
                ctx.get("vwap_deviation_pct", 0),
                rsi_tolerance=jc.rsi_tolerance,
                lookback_days=jc.lookback_days,
            )
            ctx["historical_stats"] = stats
            if (
                stats["similar_trades"] >= jc.min_trades_for_veto
                and stats["win_rate"] < jc.min_win_rate
            ):
                self.journal.log_signal(
                    self.symbol,
                    "entry_vetoed",
                    entry_signal.reason,
                    "reject",
                    1.0,
                    f"historical win_rate {stats['win_rate']:.2f} below {jc.min_win_rate}",
                    **self._indicator_kwargs(ctx),
                )
                logger.info(
                    "%s blocked by journal history: %d trades, win_rate=%.2f",
                    self.symbol,
                    stats["similar_trades"],
                    stats["win_rate"],
                )
                return

        llm_action = "approve"
        llm_confidence = 1.0
        llm_reason = "llm_disabled"

        if self.config.llm.enabled:
            decision, source = await self.llm.trade_veto(ctx)
            llm_action = decision.action
            llm_confidence = decision.confidence
            llm_reason = f"[{source}] {decision.reason}"

            if decision.action == "reject":
                self.journal.log_signal(
                    self.symbol,
                    "entry_vetoed",
                    entry_signal.reason,
                    llm_action,
                    llm_confidence,
                    llm_reason,
                    **self._indicator_kwargs(ctx),
                )
                logger.info("%s LLM vetoed entry: %s", self.symbol, llm_reason)
                return

        self.journal.log_signal(
            self.symbol,
            "entry",
            entry_signal.reason,
            llm_action,
            llm_confidence,
            llm_reason,
            **self._indicator_kwargs(ctx),
        )
        await self._submit_buy(close)

    async def _submit_buy(self, price: float) -> None:
        equity = self.executor.get_equity()
        self.risk.update_equity(equity)
        qty = calculate_position_size(
            equity,
            price,
            self.config.risk,
            self.config.strategy,
        )
        if qty < 1:
            return

        self.state = ScalpState.BUY_SUBMITTED
        if self.use_bracket:
            order = self.executor.submit_bracket_buy(self.symbol, qty, price)
        else:
            order = self.executor.submit_market_buy(self.symbol, qty)
        self.buy_order_id = str(order.id)
        self.position_qty = qty
        logger.info("%s buy submitted: %s shares @ ~%.2f", self.symbol, qty, price)

    async def _submit_sell(self, price: float, reason: str) -> None:
        if self.position_qty <= 0:
            return
        self.pending_exit_reason = reason
        self.executor.cancel_open_orders(self.symbol)
        self.state = ScalpState.SELL_SUBMITTED
        if reason in ("trailing_stop", "rsi_overbought"):
            order = self.executor.submit_market_sell(self.symbol, self.position_qty)
        else:
            limit_price = max(price, self.entry_price)
            order = self.executor.submit_limit_sell(self.symbol, self.position_qty, limit_price)
        self.sell_order_id = str(order.id)
        logger.info("%s sell submitted: %s shares (%s)", self.symbol, self.position_qty, reason)

    async def on_order_update(self, event: str, order_data: dict) -> None:
        if event != "fill":
            return

        order_id = str(order_data.get("order_id", order_data.get("id", "")))
        side = str(order_data.get("side", "")).lower()
        filled_qty = float(order_data.get("filled_qty", order_data.get("qty", 0)) or 0)
        filled_price = float(order_data.get("filled_avg_price", order_data.get("price", 0)) or 0)

        if order_id == self.buy_order_id and side in ("buy", ""):
            self.entry_price = filled_price
            self.highest_since_entry = filled_price
            self.position_qty = filled_qty
            self.state = ScalpState.IN_POSITION
            self.risk.register_open(self.symbol)
            self.journal.log_trade(
                TradeRecord(
                    symbol=self.symbol,
                    side="buy",
                    qty=filled_qty,
                    price=filled_price,
                    order_id=order_id,
                    reason="entry_fill",
                )
            )
            await self.llm.alert(
                "Trade Fill",
                f"BUY {self.symbol} x {filled_qty} @ ${filled_price:.2f}",
            )
            return

        is_sell_fill = side == "sell" or (
            self.state == ScalpState.IN_POSITION and order_id != self.buy_order_id
        )
        if is_sell_fill and self.state in (ScalpState.IN_POSITION, ScalpState.SELL_SUBMITTED):
            pnl = (filled_price - self.entry_price) * filled_qty if self.entry_price else 0
            self.risk.record_realized_pnl(pnl)
            self.risk.register_close(self.symbol)
            exit_reason = self.pending_exit_reason or "exit_fill"
            self.journal.log_trade(
                TradeRecord(
                    symbol=self.symbol,
                    side="sell",
                    qty=filled_qty,
                    price=filled_price,
                    order_id=order_id,
                    pnl=pnl,
                    reason=exit_reason,
                )
            )
            await self.llm.alert(
                "Trade Fill",
                f"SELL {self.symbol} x {filled_qty} @ ${filled_price:.2f} | P&L: ${pnl:.2f}",
            )
            self._reset()

    def _reset(self) -> None:
        self.state = ScalpState.IDLE
        self.entry_price = 0.0
        self.highest_since_entry = 0.0
        self.position_qty = 0.0
        self.buy_order_id = None
        self.sell_order_id = None
        self.pending_exit_reason = ""
