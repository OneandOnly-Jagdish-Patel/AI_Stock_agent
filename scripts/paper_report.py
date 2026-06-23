"""Print daily P&L summary from trade journal."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.journal.logger import TradeJournal


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily paper trading report")
    parser.add_argument("--date", type=str, default="", help="Date YYYY-MM-DD (default today ET)")
    args = parser.parse_args()

    config = load_config()
    journal = TradeJournal(config.journal_db_path)

    if args.date:
        date = args.date
    else:
        tz = pytz.timezone(config.session.timezone)
        date = datetime.now(tz).date().isoformat()

    summary = journal.get_daily_summary(date)
    trades = journal.get_today_trades(date)

    print(f"=== Paper Trading Report: {date} ===\n")

    if summary:
        print(f"Starting equity: ${summary['starting_equity']:,.2f}")
        print(f"Ending equity:   ${summary['ending_equity']:,.2f}")
        print(f"Net P&L:         ${summary['net_pnl']:,.2f}")
        print(f"Trades:          {summary['trade_count']}")
        print(f"Wins:            {summary['win_count']}")
    else:
        print("No daily summary recorded yet.")

    watchlist = journal.get_daily_watchlist(date)
    if watchlist:
        print(f"\n--- Screener Picks ---")
        for w in watchlist:
            print(f"  {w['symbol']:6s} [{w.get('source', '')}] {w.get('reason', '')}")

    if trades:
        print(f"\n--- Trades ({len(trades)}) ---")
        pnl_by_symbol: dict[str, float] = {}
        for t in trades:
            pnl = t.get("pnl")
            if pnl is not None and t.get("side") == "sell":
                pnl_by_symbol[t["symbol"]] = pnl_by_symbol.get(t["symbol"], 0) + pnl
            pnl_str = f" P&L ${pnl:.2f}" if pnl is not None else ""
            print(
                f"  {t['ts'][:19]} {t['side'].upper():4s} {t['symbol']} "
                f"x {t['qty']} @ ${t['price']:.2f}{pnl_str}"
            )
        if pnl_by_symbol:
            print("\n--- P&L by Symbol ---")
            for sym, pnl in sorted(pnl_by_symbol.items(), key=lambda x: -x[1]):
                print(f"  {sym}: ${pnl:.2f}")
    else:
        print("\nNo trades logged for this date.")


if __name__ == "__main__":
    main()
