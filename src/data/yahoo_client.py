"""Yahoo Finance research data via yfinance (screener, bars, quotes)."""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
import yfinance as yf

if TYPE_CHECKING:
    from src.screener.fetch import Candidate

logger = logging.getLogger(__name__)

_REQUEST_PAUSE_SEC = 0.5
_BATCH_SIZE = 25


@dataclass
class DailyMetrics:
    price: float
    volume: float
    gap_pct: float
    volume_ratio: float
    atr_pct: float
    metrics_source: str = "yahoo"


@dataclass
class QuoteSnapshot:
    symbol: str
    price: float
    change_pct: float
    volume: float
    metrics_source: str = "yahoo"


@dataclass
class IntradayBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def _pause() -> None:
    time.sleep(_REQUEST_PAUSE_SEC)


def _screen_quotes(screen_name: str, count: int) -> list[dict]:
    try:
        result = yf.screen(screen_name, count=count)
    except Exception:
        logger.warning("Yahoo screener %s failed", screen_name, exc_info=True)
        return []
    if not result:
        return []
    quotes = result.get("quotes") if isinstance(result, dict) else None
    return list(quotes or [])


def _quote_to_fields(quote: dict) -> tuple[str, float, float, float]:
    sym = str(quote.get("symbol", "")).upper()
    price = float(quote.get("regularMarketPrice") or quote.get("price") or 0)
    pct = float(quote.get("regularMarketChangePercent") or quote.get("percentChange") or 0)
    volume = float(quote.get("regularMarketVolume") or quote.get("dayvolume") or 0)
    return sym, price, pct, volume


def fetch_screener_candidates(count: int) -> list[Candidate]:
    """Fetch most actives and day gainers from Yahoo Finance."""
    from src.screener.fetch import Candidate

    per_screen = max(count // 2, 10)
    candidates: dict[str, Candidate] = {}

    for screen_name, source in (("most_actives", "yahoo_actives"), ("day_gainers", "yahoo_gainer")):
        _pause()
        for quote in _screen_quotes(screen_name, per_screen):
            sym, price, pct, volume = _quote_to_fields(quote)
            if not sym:
                continue
            existing = candidates.get(sym)
            if existing:
                if volume > existing.volume:
                    existing.volume = volume
                if pct and not existing.percent_change:
                    existing.percent_change = pct
                if price and not existing.price:
                    existing.price = price
                existing.source = f"{existing.source}+{source}"
            else:
                candidates[sym] = Candidate(
                    symbol=sym,
                    volume=volume,
                    percent_change=pct,
                    price=price,
                    source=source,
                )

    return list(candidates.values())[:count]


def _flatten_download(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize yfinance download output to OHLCV columns."""
    if data is None or data.empty:
        return pd.DataFrame()

    df = data
    if isinstance(df.columns, pd.MultiIndex):
        level0 = df.columns.get_level_values(0)
        if symbol in level0:
            df = df[symbol]
        elif "Close" in level0:
            df = df.copy()
        else:
            first = level0[0]
            df = df[first]

    df = df.rename(columns={c: str(c).title() for c in df.columns})
    return df.dropna(how="all")


def _metrics_from_history(df: pd.DataFrame) -> DailyMetrics | None:
    if df is None or df.empty or len(df) < 2:
        return None
    if "Close" not in df.columns:
        return None
    recent = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(recent["Close"])
    if close <= 0:
        return None
    prev_close = float(prev["Close"])
    atr = float(recent["High"]) - float(recent["Low"])
    vol_ratio = float(recent["Volume"]) / float(prev["Volume"]) if float(prev["Volume"]) > 0 else 1.0
    gap_pct = ((float(recent["Open"]) - prev_close) / prev_close) * 100 if prev_close else 0.0
    return DailyMetrics(
        price=close,
        volume=float(recent["Volume"]),
        gap_pct=round(gap_pct, 2),
        volume_ratio=round(vol_ratio, 2),
        atr_pct=round((atr / close) * 100, 2),
    )


def fetch_daily_metrics(symbols: list[str], days: int = 5) -> dict[str, DailyMetrics]:
    """Batch daily OHLCV metrics for symbols."""
    if not symbols:
        return {}

    result: dict[str, DailyMetrics] = {}
    period = f"{max(days + 2, 7)}d"

    for i in range(0, len(symbols), _BATCH_SIZE):
        batch = symbols[i : i + _BATCH_SIZE]
        _pause()
        try:
            data = yf.download(
                batch,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception:
            logger.warning("Yahoo daily download failed for batch", exc_info=True)
            continue

        if data is None or data.empty:
            continue

        if len(batch) == 1:
            sym = batch[0]
            sym_df = _flatten_download(data, sym)
            metrics = _metrics_from_history(sym_df)
            if metrics:
                result[sym] = metrics
            continue

        for sym in batch:
            if not isinstance(data.columns, pd.MultiIndex) or sym not in data.columns.get_level_values(0):
                continue
            sym_df = _flatten_download(data[sym], sym)
            metrics = _metrics_from_history(sym_df)
            if metrics:
                result[sym] = metrics

    return result


def fetch_recent_daily_closes(symbol: str, days: int = 5) -> list[dict[str, float | str]]:
    """Return the last N daily closes (oldest first) for entry trend context."""
    period = f"{max(days + 2, 7)}d"
    _pause()
    try:
        data = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        logger.warning("Yahoo daily close history failed for %s", symbol, exc_info=True)
        return []

    if data is None or data.empty:
        return []

    df = _flatten_download(data, symbol)
    if df is None or df.empty or "Close" not in df.columns:
        return []

    tail = df.tail(days)
    bars: list[dict[str, float | str]] = []
    for idx, row in tail.iterrows():
        close = float(row["Close"])
        if close <= 0:
            continue
        date_str = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
        bars.append({"date": date_str, "close": round(close, 4)})
    return bars


def fetch_universe_ranked_by_volume(symbols: list[str], top: int) -> list[Candidate]:
    """Rank universe symbols by latest daily volume via Yahoo."""
    from src.screener.fetch import Candidate

    metrics = fetch_daily_metrics(symbols, days=3)
    candidates: list[Candidate] = []
    for sym in symbols:
        m = metrics.get(sym)
        if not m:
            continue
        candidates.append(
            Candidate(
                symbol=sym,
                volume=m.volume,
                percent_change=m.gap_pct,
                price=m.price,
                source="yahoo_universe",
            )
        )
    candidates.sort(key=lambda c: c.volume, reverse=True)
    return candidates[:top]


def fetch_intraday_bars(
    symbols: list[str],
    period: str = "2d",
    interval: str = "1m",
) -> dict[str, list[IntradayBar]]:
    """Fetch minute bars for warmup fallback."""
    if not symbols:
        return {}

    out: dict[str, list[IntradayBar]] = {}
    for i in range(0, len(symbols), _BATCH_SIZE):
        batch = symbols[i : i + _BATCH_SIZE]
        _pause()
        try:
            data = yf.download(
                batch,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception:
            logger.warning("Yahoo intraday download failed", exc_info=True)
            continue

        if data is None or data.empty:
            continue

        if len(batch) == 1:
            sym = batch[0]
            sym_df = _flatten_download(data, sym)
            out[sym] = _history_to_intraday_bars(sym_df)
            continue

        for sym in batch:
            if not isinstance(data.columns, pd.MultiIndex) or sym not in data.columns.get_level_values(0):
                continue
            sym_df = _flatten_download(data[sym], sym)
            bars = _history_to_intraday_bars(sym_df)
            if bars:
                out[sym] = bars

    return out


def _history_to_intraday_bars(df: pd.DataFrame) -> list[IntradayBar]:
    bars: list[IntradayBar] = []
    if df is None or df.empty or "Close" not in df.columns:
        return bars
    for ts, row in df.iterrows():
        if pd.isna(row.get("Close")):
            continue
        bars.append(
            IntradayBar(
                timestamp=str(ts),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0) or 0),
            )
        )
    return bars


def fetch_quote_snapshot(symbols: list[str]) -> dict[str, QuoteSnapshot]:
    """Lightweight price/change snapshot for watchlist ranking."""
    if not symbols:
        return {}

    result: dict[str, QuoteSnapshot] = {}
    for i in range(0, len(symbols), _BATCH_SIZE):
        batch = symbols[i : i + _BATCH_SIZE]
        _pause()
        try:
            tickers = yf.Tickers(" ".join(batch))
        except Exception:
            logger.warning("Yahoo quote snapshot failed", exc_info=True)
            continue

        for sym in batch:
            try:
                info = tickers.tickers[sym].fast_info
                price = float(getattr(info, "last_price", 0) or 0)
                prev = float(getattr(info, "previous_close", 0) or 0)
                change_pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0
                volume = float(getattr(info, "last_volume", 0) or 0)
                if price > 0:
                    result[sym] = QuoteSnapshot(
                        symbol=sym,
                        price=price,
                        change_pct=round(change_pct, 2),
                        volume=volume,
                    )
            except Exception:
                logger.debug("Yahoo fast_info failed for %s", sym, exc_info=True)

    return result


def fetch_finnhub_quote(symbol: str, api_key: str) -> QuoteSnapshot | None:
    """Optional Finnhub fallback for a single symbol quote."""
    if not api_key:
        return None
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        price = float(data.get("c") or 0)
        prev = float(data.get("pc") or 0)
        if price <= 0:
            return None
        change_pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0
        return QuoteSnapshot(symbol=symbol, price=price, change_pct=round(change_pct, 2), volume=0, metrics_source="finnhub")
    except Exception:
        logger.debug("Finnhub quote failed for %s", symbol, exc_info=True)
        return None


def prev_day_close_from_bars(bars: list[IntradayBar], today: date | None = None) -> float:
    """Last close from a day before today in intraday bar list."""
    today = today or date.today()
    prev_close = 0.0
    for bar in bars:
        try:
            bar_date = pd.Timestamp(bar.timestamp).date()
        except Exception:
            continue
        if bar_date < today:
            prev_close = bar.close
    return prev_close
