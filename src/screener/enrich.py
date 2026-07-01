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
from src.data.news_parse import article_headline, article_symbols, extract_news_articles
from src.data.yahoo_client import fetch_daily_metrics, fetch_finnhub_quote
from src.screener.fetch import Candidate

logger = logging.getLogger(__name__)


def _enrich_from_alpaca_bars(symbols: list[str], config: AppConfig) -> dict[str, dict]:
    bar_map: dict[str, dict] = {}
    bar_client = StockHistoricalDataClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)
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
                "metrics_source": "alpaca",
            }
    except Exception:
        logger.warning("Failed to enrich bar metrics from Alpaca", exc_info=True)
    return bar_map


def _enrich_from_yahoo(symbols: list[str], config: AppConfig) -> dict[str, dict]:
    bar_map: dict[str, dict] = {}
    try:
        metrics = fetch_daily_metrics(symbols, days=5)
        for sym, m in metrics.items():
            bar_map[sym] = {
                "price": m.price,
                "volume": m.volume,
                "gap_pct": m.gap_pct,
                "volume_ratio": m.volume_ratio,
                "atr_pct": m.atr_pct,
                "metrics_source": m.metrics_source,
            }
    except Exception:
        logger.warning("Failed to enrich bar metrics from Yahoo", exc_info=True)

    if config.research.finnhub_fallback and config.finnhub_api_key:
        for sym in symbols:
            if sym in bar_map:
                continue
            quote = fetch_finnhub_quote(sym, config.finnhub_api_key)
            if quote:
                bar_map[sym] = {
                    "price": quote.price,
                    "volume": quote.volume,
                    "gap_pct": quote.change_pct,
                    "volume_ratio": 1.0,
                    "atr_pct": 0.0,
                    "metrics_source": quote.metrics_source,
                }
    return bar_map


def enrich_candidates(candidates: list[Candidate], config: AppConfig) -> list[dict]:
    if not candidates:
        return []

    symbols = [c.symbol for c in candidates]
    if config.research.provider == "yahoo" and config.research.yahoo_enabled:
        bar_map = _enrich_from_yahoo(symbols, config)
    else:
        bar_map = _enrich_from_alpaca_bars(symbols, config)

    end = datetime.now(timezone.utc)
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
        for article in extract_news_articles(news):
            for sym in article_symbols(article):
                if sym not in headlines:
                    headlines[sym] = article_headline(article)
    except Exception:
        logger.debug("News enrich skipped", exc_info=True)

    enriched: list[dict] = []
    for c in candidates:
        sym = c.symbol
        metrics = bar_map.get(sym, {})
        metrics_available = bool(metrics)
        gap_pct = metrics.get("gap_pct", c.percent_change if c.percent_change else 0)
        enriched.append(
            {
                "symbol": sym,
                "volume": c.volume or metrics.get("volume", 0),
                "percent_change": round(c.percent_change, 2),
                "price": c.price or metrics.get("price", 0),
                "gap_pct": gap_pct,
                "volume_ratio": metrics.get("volume_ratio", 1.0),
                "atr_pct": metrics.get("atr_pct", 0),
                "headline": headlines.get(sym, ""),
                "source": c.source,
                "metrics_available": metrics_available,
                "metrics_source": metrics.get("metrics_source", "none"),
            }
        )
    return enriched
