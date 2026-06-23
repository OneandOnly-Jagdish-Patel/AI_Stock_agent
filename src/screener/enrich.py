"""Enrich candidates with metrics and headlines."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.config import AppConfig
from src.data.bars import _parse_feed
from src.screener.fetch import Candidate

logger = logging.getLogger(__name__)


def enrich_candidates(candidates: list[Candidate], config: AppConfig) -> list[dict]:
    if not candidates:
        return []

    symbols = [c.symbol for c in candidates]
    bar_client = StockHistoricalDataClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)

    bar_map: dict[str, dict] = {}
    try:
        bars = bar_client.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                feed=_parse_feed(config.alpaca_data_feed),
            )
        )
        for sym in symbols:
            if sym not in bars.data or len(bars.data[sym]) < 2:
                continue
            recent = bars.data[sym][-1]
            prev = bars.data[sym][-2]
            atr = float(recent.high) - float(recent.low)
            atr_pct = (atr / float(recent.close)) * 100 if recent.close else 0
            vol_ratio = float(recent.volume) / float(prev.volume) if prev.volume else 1.0
            gap_pct = ((float(recent.open) - float(prev.close)) / float(prev.close)) * 100 if prev.close else 0
            bar_map[sym] = {
                "price": float(recent.close),
                "volume": float(recent.volume),
                "gap_pct": round(gap_pct, 2),
                "volume_ratio": round(vol_ratio, 2),
                "atr_pct": round(atr_pct, 2),
            }
    except Exception:
        logger.warning("Failed to enrich bar metrics", exc_info=True)

    headlines: dict[str, str] = {}
    try:
        news_client = NewsClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
        )
        news = news_client.get_news(
            NewsRequest(
                symbols=",".join(symbols[:15]),
                start=end - timedelta(hours=24),
                limit=30,
                include_content=False,
            )
        )
        news_list = news.news if hasattr(news, "news") else news
        for article in news_list:
            for sym in article.symbols or []:
                if sym not in headlines:
                    headlines[sym] = article.headline
    except Exception:
        logger.debug("News enrich skipped", exc_info=True)

    enriched: list[dict] = []
    for c in candidates:
        sym = c.symbol
        metrics = bar_map.get(sym, {})
        enriched.append(
            {
                "symbol": sym,
                "volume": c.volume or metrics.get("volume", 0),
                "percent_change": round(c.percent_change, 2),
                "price": c.price or metrics.get("price", 0),
                "gap_pct": metrics.get("gap_pct", 0),
                "volume_ratio": metrics.get("volume_ratio", 1.0),
                "atr_pct": metrics.get("atr_pct", 0),
                "headline": headlines.get(sym, ""),
                "source": c.source,
            }
        )
    return enriched
