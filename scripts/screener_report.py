"""Print daily screener watchlist and picks."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.journal.logger import TradeJournal
from src.llm.router import LLMRouter
from src.screener.daily import build_daily_watchlist


def print_stored_report(journal: TradeJournal, date: str) -> None:
    entries = journal.get_daily_watchlist(date)
    if not entries:
        print(f"No screener data for {date}")
        return
    print(f"=== Screener Report: {date} ===\n")
    for e in entries:
        reason = e.get("reason") or ""
        source = e.get("source") or ""
        print(f"  {e['symbol']:6s}  [{source:8s}]  {reason}")


async def run_live() -> None:
    config = load_config()
    journal = TradeJournal(config.journal_db_path)
    llm = LLMRouter(config.llm)

    if not config.alpaca_api_key:
        print("Set ALPACA_API_KEY in .env")
        return

    result = await build_daily_watchlist(config, llm, journal)
    print("=== Live Screener ===\n")
    print(f"Watchlist: {', '.join(result.symbols)}")
    print(f"Dynamic picks: {', '.join(result.dynamic_picks) or 'none'}")
    print(f"Summary: {result.summary}\n")
    for sym in result.dynamic_picks:
        print(f"  {sym}: {result.reasons.get(sym, '')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily screener report")
    parser.add_argument("--date", type=str, default="", help="Date YYYY-MM-DD (read from DB)")
    parser.add_argument("--dry-run", action="store_true", help="Run screener live now")
    args = parser.parse_args()

    if args.dry_run:
        asyncio.run(run_live())
        return

    config = load_config()
    journal = TradeJournal(config.journal_db_path)
    tz = pytz.timezone(config.session.timezone)
    date = args.date or datetime.now(tz).date().isoformat()
    print_stored_report(journal, date)


if __name__ == "__main__":
    main()
