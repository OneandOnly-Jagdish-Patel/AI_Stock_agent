"""Replay minute-bar strategy on historical data."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.config import load_config
from src.data.bars import _parse_feed
from src.strategy.indicators import Bar, IndicatorState, Quote
from src.strategy.signals import SignalType, evaluate_entry, evaluate_exit

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_backtest(days: int = 30) -> None:
    config = load_config()
    if not config.alpaca_api_key:
        logger.error("Set ALPACA_API_KEY in .env")
        return

    client = StockHistoricalDataClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    request = StockBarsRequest(
        symbol_or_symbols=config.symbols,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        feed=_parse_feed(config.alpaca_data_feed),
    )
    bars = client.get_stock_bars(request)

    total_trades = 0
    wins = 0
    total_pnl = 0.0

    for symbol in config.symbols:
        if symbol not in bars.data:
            continue
        state = IndicatorState()
        in_position = False
        entry_price = 0.0
        highest = 0.0
        symbol_pnl = 0.0
        symbol_trades = 0

        for b in bars.data[symbol]:
            bar = Bar(
                timestamp=str(b.timestamp),
                open=float(b.open),
                high=float(b.high),
                low=float(b.low),
                close=float(b.close),
                volume=float(b.volume),
            )
            state.add_bar(bar)
            close = bar.close

            if in_position:
                highest = max(highest, close)
                exit_sig = evaluate_exit(
                    entry_price,
                    close,
                    highest,
                    config.strategy,
                    state.rsi(config.strategy.rsi_period),
                )
                if exit_sig.signal_type == SignalType.SELL:
                    pnl = close - entry_price
                    symbol_pnl += pnl
                    symbol_trades += 1
                    if pnl > 0:
                        wins += 1
                    in_position = False
                continue

            fake_quote = Quote(
                symbol=symbol,
                bid=close * 0.9999,
                ask=close * 1.0001,
                timestamp=str(b.timestamp),
            )
            entry_sig = evaluate_entry(symbol, state, fake_quote, config.strategy, config.execution)
            if entry_sig.signal_type == SignalType.BUY:
                in_position = True
                entry_price = close
                highest = close

        total_trades += symbol_trades
        total_pnl += symbol_pnl
        logger.info(
            "%s: %d trades, P&L per share $%.4f",
            symbol,
            symbol_trades,
            symbol_pnl,
        )

    win_rate = (wins / total_trades * 100) if total_trades else 0
    logger.info("---")
    logger.info("Total round-trip trades: %d", total_trades)
    logger.info("Win rate: %.1f%%", win_rate)
    logger.info("Total P&L (per share, no sizing): $%.4f", total_pnl)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest scalping rules on minute bars")
    parser.add_argument("--days", type=int, default=30, help="Days of history")
    args = parser.parse_args()
    run_backtest(args.days)
