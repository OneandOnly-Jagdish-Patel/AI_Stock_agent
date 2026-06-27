#!/usr/bin/env python3
"""Recompute daily_pnl net_pnl and trade counts from the trades table."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.journal.logger import TradeJournal


def main() -> None:
    config = load_config()
    journal = TradeJournal(config.journal_db_path)
    count = journal.backfill_daily_pnl()
    print(f"Backfilled {count} daily_pnl row(s) in {config.journal_db_path}")


if __name__ == "__main__":
    main()
