"""Load fallback universe symbol list."""

from __future__ import annotations

from pathlib import Path

from src.config import PROJECT_ROOT


def load_universe() -> list[str]:
    path = PROJECT_ROOT / "data" / "universe" / "sp500_liquid.txt"
    if not path.exists():
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD", "GOOGL"]
    symbols: list[str] = []
    for line in path.read_text().splitlines():
        sym = line.strip().upper()
        if sym and not sym.startswith("#"):
            symbols.append(sym)
    return symbols
