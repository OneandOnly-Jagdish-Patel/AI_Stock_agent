"""Trading agent orchestrator."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.briefing.premarket import run_briefing
from src.config import AppConfig, load_config
from src.data.bars import BarManager
from src.data.stream import MarketDataStream
from src.data.trade_stream import OrderUpdateStream
from src.execution.orders import OrderExecutor
from src.execution.positions import PositionManager
from src.journal.logger import TradeJournal
from src.llm.router import LLMRouter
from src.risk.manager import RiskManager
from src.screener.daily import build_daily_watchlist
from src.strategy.scalper import SymbolScalper

_log_dir = Path(__file__).resolve().parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).resolve().parent.parent / "logs" / "agent.log"),
    ],
)
logger = logging.getLogger(__name__)


class TradingAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.journal = TradeJournal(config.journal_db_path)
        self.executor = OrderExecutor(config)
        self.positions = PositionManager(config)
        self.risk = RiskManager(config, self.positions)
        self.llm = LLMRouter(config.llm)
        self.bar_manager = BarManager(config)
        self.scalpers: dict[str, SymbolScalper] = {}
        self.active_symbols: list[str] = list(config.symbols)
        self.avoided_symbols: set[str] = set()
        self._stream: MarketDataStream | None = None
        self._trade_stream: OrderUpdateStream | None = None
        self._running = False
        self._watchlist_task: asyncio.Task | None = None
        self._session_closed_date: str | None = None

    def _in_trading_session(self) -> bool:
        tz = pytz.timezone(self.config.session.timezone)
        now = datetime.now(tz)
        if now.weekday() >= 5:
            return False
        start_h, start_m = map(int, self.config.session.start_time.split(":"))
        end_h, end_m = map(int, self.config.session.end_time.split(":"))
        start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        return start <= now <= end

    async def _wait_until_time(self, time_str: str) -> None:
        tz = pytz.timezone(self.config.session.timezone)
        now = datetime.now(tz)
        if now.weekday() >= 5:
            return
        h, m = map(int, time_str.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if now < target:
            wait_secs = (target - now).total_seconds()
            logger.info("Waiting %.0f seconds until %s ET", wait_secs, time_str)
            await asyncio.sleep(wait_secs)

    async def _run_screener(self) -> None:
        if not self.config.screener.enabled or self.config.screener.mode == "static":
            self.active_symbols = list(self.config.symbols)
            logger.info("Using static watchlist: %s", self.active_symbols)
            return

        await self._wait_until_time(self.config.screener.run_time)
        result = await build_daily_watchlist(self.config, self.llm, self.journal)
        self.active_symbols = result.symbols

        lines = [f"Today's watchlist: {', '.join(result.symbols)}"]
        for sym in result.dynamic_picks:
            reason = result.reasons.get(sym, "")
            lines.append(f"  {sym}: {reason}")
        lines.append(f"Summary: {result.summary}")
        msg = "\n".join(lines)
        logger.info("Screener result: %s", msg.replace("\n", " | "))
        await self.llm.alert("Daily Screener", msg)

    async def _wait_until_briefing_time(self) -> None:
        if not self.config.briefing.enabled:
            return
        await self._wait_until_time(self.config.briefing.time)

    async def _run_premarket_briefing(self) -> None:
        if not self.config.briefing.enabled:
            return
        await self._wait_until_briefing_time()
        briefing = await run_briefing(self.config, self.llm, self.active_symbols)
        self.avoided_symbols = {s.upper() for s in briefing.avoid}
        msg = (
            f"Avoid: {', '.join(briefing.avoid) or 'none'}\n"
            f"Caution: {', '.join(briefing.caution) or 'none'}\n"
            f"Reason: {briefing.reason}"
        )
        logger.info("Pre-market briefing: %s", msg.replace("\n", " | "))
        self.journal.log_event("premarket_briefing", msg)
        await self.llm.alert("Pre-Market Briefing", msg)

    async def _on_bar(self, symbol: str, bar_data: dict) -> None:
        if not self._in_trading_session():
            return
        if self.risk.is_killed():
            return

        state = self.bar_manager.on_bar(symbol, bar_data)
        scalper = self.scalpers.get(symbol)
        if scalper:
            await scalper.on_bar(state)

    async def _watchlist_loop(self) -> None:
        interval = self.config.llm.watchlist_interval_minutes * 60
        while self._running:
            await asyncio.sleep(interval)
            if not self._in_trading_session() or not self.config.llm.enabled:
                continue
            context = {}
            for symbol, state in self.bar_manager.states.items():
                context[symbol] = {
                    "rsi": state.rsi(self.config.strategy.rsi_period),
                    "vwap_dev": state.vwap_deviation_pct(),
                    "close": state.latest_close(),
                }
            ranking = await self.llm.rank_watchlist(context)
            if ranking:
                logger.info("Watchlist ranking: %s — %s", ranking.ranked, ranking.reason)
                self.journal.log_event("watchlist_rank", str(ranking.ranked))

    async def _on_order_update(self, event: str, order_data: dict) -> None:
        symbol = order_data.get("symbol", "")
        scalper = self.scalpers.get(symbol)
        if scalper:
            await scalper.on_order_update(event, order_data)

    async def _session_guard_loop(self) -> None:
        tz = pytz.timezone(self.config.session.timezone)
        while self._running:
            await asyncio.sleep(30)
            now = datetime.now(tz)
            today = now.date().isoformat()
            end_h, end_m = map(int, self.config.session.end_time.split(":"))
            end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

            if now > end and today != self._session_closed_date:
                self._session_closed_date = today
                logger.info("Session ended — flattening positions")
                self.positions.flatten_all()
                equity = self.executor.get_equity()
                trades = self.journal.get_today_trades(today)
                wins = sum(1 for t in trades if t.get("pnl") and t["pnl"] > 0)
                self.journal.upsert_daily_pnl(
                    today,
                    self.risk.state.starting_equity,
                    equity,
                    len(trades),
                    wins,
                )
                summary_ctx = {
                    "date": today,
                    "equity": equity,
                    "trades": len(trades),
                    "wins": wins,
                }
                summary = await self.llm.openclaw.daily_summary(summary_ctx)
                await self.llm.alert("Daily P&L Summary", summary)

            if self.risk.is_killed():
                logger.warning("Kill switch active — flattening and stopping")
                self.positions.flatten_all()
                await self.llm.alert("Kill Switch", self.risk.state.kill_reason)
                self._running = False
                if self._stream:
                    self._stream.stop()
                if self._trade_stream:
                    self._trade_stream.stop()

    async def run(self) -> None:
        if not self.config.alpaca_api_key or not self.config.alpaca_secret_key:
            logger.error("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env")
            return

        self._running = True
        equity = self.executor.get_equity()
        tz = pytz.timezone(self.config.session.timezone)
        today = datetime.now(tz).date()
        self.risk.reset_session(equity, today)

        logger.info("Account equity: $%.2f", equity)
        ollama_ok = await self.llm.check_health()
        logger.info("Ollama health: %s (model=%s)", ollama_ok, self.config.llm.ollama_model)

        await self._run_screener()
        await self._run_premarket_briefing()

        self.bar_manager.set_symbols(self.active_symbols)
        self.bar_manager.warmup(self.active_symbols)

        self._stream = MarketDataStream(self.config, self.active_symbols, on_bar=self._on_bar)
        self._trade_stream = OrderUpdateStream(self.config, on_update=self._on_order_update)
        for symbol in self.active_symbols:
            self.scalpers[symbol] = SymbolScalper(
                symbol,
                self.config,
                self.executor,
                self.risk,
                self.journal,
                self.llm,
                self._stream,
                avoided_symbols=self.avoided_symbols,
            )

        self._watchlist_task = asyncio.create_task(self._watchlist_loop())
        session_task = asyncio.create_task(self._session_guard_loop())

        await self.llm.alert(
            "Agent Started",
            f"Paper trading agent started. Symbols: {', '.join(self.active_symbols)}",
        )

        try:
            await asyncio.gather(
                self._stream.run(),
                self._trade_stream.run(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            if self._watchlist_task:
                self._watchlist_task.cancel()
            session_task.cancel()
            if self._stream:
                self._stream.stop()
            if self._trade_stream:
                self._trade_stream.stop()
            if self.risk.is_killed():
                self.positions.flatten_all()
                await self.llm.alert("Kill Switch", self.risk.state.kill_reason)


def main() -> None:
    config = load_config()
    agent = TradingAgent(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown_handler(*_: object) -> None:
        logger.info("Shutdown signal received")
        agent._running = False
        if agent._stream:
            agent._stream.stop()
        if agent._trade_stream:
            agent._trade_stream.stop()
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        loop.run_until_complete(agent.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
