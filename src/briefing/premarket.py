"""Pre-market news briefing and symbol avoid list."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest

from src.config import AppConfig
from src.llm.ollama_client import PremarketBriefing
from src.llm.router import LLMRouter

logger = logging.getLogger(__name__)

RISK_KEYWORDS = ("earnings", "fda", "guidance", "downgrade", "lawsuit", "sec ", "investigation")


def _fetch_news(config: AppConfig, symbols: list[str]) -> list[dict]:
    client = NewsClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    start = datetime.now(timezone.utc) - timedelta(hours=config.briefing.news_lookback_hours)
    request = NewsRequest(
        symbols=",".join(symbols),
        start=start,
        limit=config.briefing.news_limit,
        include_content=False,
    )
    try:
        result = client.get_news(request)
    except Exception:
        logger.exception("Failed to fetch pre-market news")
        return []

    items: list[dict] = []
    news_list = result.news if hasattr(result, "news") else result
    for article in news_list:
        items.append(
            {
                "symbols": list(article.symbols) if article.symbols else [],
                "headline": article.headline,
                "source": article.source,
                "created_at": str(article.created_at),
            }
        )
    return items


def _keyword_flags(news: list[dict], symbols: list[str]) -> dict[str, list[str]]:
    flags: dict[str, list[str]] = {s: [] for s in symbols}
    for article in news:
        headline = (article.get("headline") or "").lower()
        matched = [kw for kw in RISK_KEYWORDS if kw in headline]
        if not matched:
            continue
        for sym in article.get("symbols", []):
            if sym in flags:
                flags[sym].extend(matched)
    return {sym: list(set(hits)) for sym, hits in flags.items() if hits}


async def run_briefing(config: AppConfig, llm: LLMRouter, symbols: list[str] | None = None) -> PremarketBriefing:
    watchlist = symbols or config.symbols
    news = _fetch_news(config, watchlist)
    keyword_flags = _keyword_flags(news, watchlist)
    context = {
        "symbols": watchlist,
        "news": news,
        "keyword_flags": keyword_flags,
    }

    if not config.briefing.enabled:
        return PremarketBriefing(avoid=[], caution=[], reason="briefing disabled")

    if not news:
        logger.warning("No news available for pre-market briefing")
        keyword_avoid = list(keyword_flags.keys())
        return PremarketBriefing(
            avoid=keyword_avoid,
            caution=[],
            reason="No news feed — keyword flags only",
        )

    return await llm.briefing_decision(context)
