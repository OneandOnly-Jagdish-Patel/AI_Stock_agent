"""Fetch screener candidates from Yahoo (research) or Alpaca with fallbacks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from alpaca.data.enums import MarketType, MostActivesBy
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.screener import ScreenerClient
from alpaca.data.requests import MarketMoversRequest, MostActivesRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.config import AppConfig
from src.data.bars import _parse_feed
from src.data.yahoo_client import fetch_screener_candidates as yahoo_fetch_screener
from src.data.yahoo_client import fetch_universe_ranked_by_volume
from src.screener.universe import load_universe

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    symbol: str
    volume: float = 0.0
    percent_change: float = 0.0
    price: float = 0.0
    source: str = "screener"


def fetch_from_alpaca_screener(config: AppConfig) -> list[Candidate]:
    client = ScreenerClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    candidates: dict[str, Candidate] = {}
    top = config.screener.candidate_pool_size

    try:
        actives = client.get_most_actives(MostActivesRequest(top=top, by=MostActivesBy.VOLUME))
        for stock in actives.most_actives:
            candidates[stock.symbol] = Candidate(
                symbol=stock.symbol,
                volume=float(stock.volume),
                source="most_actives",
            )
    except Exception:
        logger.warning("Alpaca most_actives failed, will use fallback", exc_info=True)

    try:
        movers = client.get_market_movers(MarketMoversRequest(market_type=MarketType.STOCKS, top=top))
        for mover in movers.gainers:
            existing = candidates.get(mover.symbol)
            if existing:
                existing.percent_change = float(mover.percent_change)
                existing.price = float(mover.price)
                existing.source = "actives+gainer"
            else:
                candidates[mover.symbol] = Candidate(
                    symbol=mover.symbol,
                    percent_change=float(mover.percent_change),
                    price=float(mover.price),
                    source="gainer",
                )
    except Exception:
        logger.warning("Alpaca market_movers failed", exc_info=True)

    return list(candidates.values())


def fetch_from_universe_bars(config: AppConfig) -> list[Candidate]:
    """Fallback: rank universe symbols by yesterday's volume."""
    symbols = load_universe()
    anchors = set(config.screener.anchor_symbols)
    symbols = [s for s in symbols if s not in anchors][:50]
    top = config.screener.candidate_pool_size

    if config.research.provider == "yahoo" and config.research.yahoo_enabled:
        try:
            ranked = fetch_universe_ranked_by_volume(symbols, top)
            if ranked:
                logger.info("Universe fallback via Yahoo: %d candidates", len(ranked))
                return ranked
        except Exception:
            logger.warning("Yahoo universe fallback failed", exc_info=True)

    client = StockHistoricalDataClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=3)
    try:
        bars = client.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                feed=_parse_feed(config.alpaca_data_feed),
            )
        )
    except Exception:
        logger.exception("Universe bar fallback failed")
        return []

    candidates: list[Candidate] = []
    for symbol in symbols:
        if symbol not in bars.data or not bars.data[symbol]:
            continue
        day_bar = bars.data[symbol][-1]
        prev = bars.data[symbol][-2] if len(bars.data[symbol]) > 1 else day_bar
        pct = ((float(day_bar.close) - float(prev.close)) / float(prev.close)) * 100 if prev.close else 0
        candidates.append(
            Candidate(
                symbol=symbol,
                volume=float(day_bar.volume),
                percent_change=pct,
                price=float(day_bar.close),
                source="fallback",
            )
        )
    candidates.sort(key=lambda c: c.volume, reverse=True)
    return candidates[:top]


def fetch_candidates(config: AppConfig) -> list[Candidate]:
    if config.research.provider == "yahoo" and config.research.yahoo_enabled:
        try:
            candidates = yahoo_fetch_screener(config.screener.candidate_pool_size)
            if candidates:
                logger.info("Yahoo screener returned %d candidates", len(candidates))
                return candidates
            logger.warning("Yahoo screener returned no candidates, falling back to Alpaca")
        except Exception:
            logger.warning("Yahoo screener failed, falling back to Alpaca", exc_info=True)

    candidates = fetch_from_alpaca_screener(config)
    if not candidates:
        logger.info("Using universe fallback for screener candidates")
        candidates = fetch_from_universe_bars(config)
    return candidates
