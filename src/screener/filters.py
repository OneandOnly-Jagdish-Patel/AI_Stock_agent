"""Rule-based filters for screener candidates."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.config import AppConfig
from src.journal.logger import TradeJournal
from src.screener.fetch import Candidate

logger = logging.getLogger(__name__)


def _fetch_earnings_today(config: AppConfig) -> set[str]:
    if not config.screener.finnhub_enabled or not config.finnhub_api_key:
        return set()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    req_url = f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={today}&token={config.finnhub_api_key}"
    try:
        import json
        import urllib.request

        with urllib.request.urlopen(req_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        symbols = {e.get("symbol", "").upper() for e in data.get("earningsCalendar", []) if e.get("symbol")}
        return symbols
    except Exception:
        logger.warning("Finnhub earnings calendar fetch failed", exc_info=True)
        return set()


def _yesterday_losers(journal: TradeJournal) -> set[str]:
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    trades = journal.get_today_trades(yesterday)
    losers: set[str] = set()
    for t in trades:
        if t.get("side") == "sell" and t.get("pnl") is not None and t["pnl"] < 0:
            losers.add(t["symbol"].upper())
    return losers


def apply_filters(
    candidates: list[Candidate],
    config: AppConfig,
    journal: TradeJournal | None = None,
) -> list[Candidate]:
    sc = config.screener
    anchors = {s.upper() for s in sc.anchor_symbols}
    earnings_today = _fetch_earnings_today(config)
    losers = _yesterday_losers(journal) if journal and sc.exclude_yesterday_losers else set()

    filtered: list[Candidate] = []
    for c in candidates:
        sym = c.symbol.upper()
        if sym in anchors:
            continue
        if c.price and (c.price < sc.min_price or c.price > sc.max_price):
            continue
        if c.volume and c.volume < sc.min_volume:
            continue
        if abs(c.percent_change) > sc.max_percent_change:
            continue
        if sym in earnings_today:
            logger.debug("Filtered %s: earnings today", sym)
            continue
        if sym in losers:
            logger.debug("Filtered %s: yesterday loser", sym)
            continue
        filtered.append(c)

    return filtered
