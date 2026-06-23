"""Daily screener orchestrator — builds hybrid watchlist."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import pytz

from src.config import AppConfig
from src.journal.logger import TradeJournal
from src.llm.router import LLMRouter
from src.screener.enrich import enrich_candidates
from src.screener.fetch import fetch_candidates
from src.screener.filters import apply_filters
from src.screener.rank import rank_candidates

logger = logging.getLogger(__name__)


@dataclass
class DailyWatchlistResult:
    symbols: list[str]
    dynamic_picks: list[str]
    reasons: dict[str, str]
    summary: str


def resolve_active_symbols(config: AppConfig) -> list[str]:
    """Return symbols for static mode without running screener."""
    if config.screener.mode == "static" or not config.screener.enabled:
        return list(config.symbols)
    if config.screener.mode == "dynamic":
        return []
    return list(config.screener.anchor_symbols)


async def build_daily_watchlist(
    config: AppConfig,
    llm: LLMRouter,
    journal: TradeJournal,
) -> DailyWatchlistResult:
    sc = config.screener
    tz = pytz.timezone(config.session.timezone)
    today = datetime.now(tz).date().isoformat()

    if sc.mode == "static" or not sc.enabled:
        symbols = list(config.symbols)
        return DailyWatchlistResult(
            symbols=symbols,
            dynamic_picks=[],
            reasons={},
            summary="static watchlist from config",
        )

    anchors = [s.upper() for s in sc.anchor_symbols]
    raw = fetch_candidates(config)
    filtered = apply_filters(raw, config, journal)
    enriched = enrich_candidates(filtered, config)

    # Exclude anchors from dynamic pool
    enriched = [c for c in enriched if c["symbol"] not in anchors]

    ranking = await rank_candidates(enriched, config, llm)
    dynamic = [p.upper() for p in ranking.picks[: sc.dynamic_slots]]

    if sc.mode == "hybrid":
        symbols = anchors + dynamic
    else:
        symbols = dynamic

    entries: list[dict] = []
    rank = 0
    for sym in anchors:
        entries.append({"symbol": sym, "source": "anchor", "rank": rank, "metrics": {}, "reason": "fixed anchor"})
        rank += 1
    for sym in dynamic:
        entries.append(
            {
                "symbol": sym,
                "source": "screener",
                "rank": rank,
                "metrics": next((c for c in enriched if c["symbol"] == sym), {}),
                "reason": ranking.reasons.get(sym, ""),
            }
        )
        rank += 1

    journal.save_daily_watchlist(today, entries)
    journal.log_event("daily_screener", f"Watchlist: {', '.join(symbols)}")

    logger.info("Daily watchlist: %s (dynamic: %s)", symbols, dynamic)
    return DailyWatchlistResult(
        symbols=symbols,
        dynamic_picks=dynamic,
        reasons=ranking.reasons,
        summary=ranking.summary,
    )
