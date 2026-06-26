"""FastAPI dashboard API — read-only view of journal, config, and agent logs."""

from __future__ import annotations

import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import PROJECT_ROOT, load_config
from src.journal.logger import TradeJournal

app = FastAPI(title="AI Trading Agent Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_config = load_config()
_journal = TradeJournal(_config.journal_db_path)
_log_path = PROJECT_ROOT / "logs" / "agent.log"


def _today_et() -> str:
    tz = pytz.timezone(_config.session.timezone)
    return datetime.now(tz).date().isoformat()


def _sanitize_config() -> dict[str, Any]:
    return {
        "symbols": _config.symbols,
        "strategy": _config.strategy.__dict__,
        "session": _config.session.__dict__,
        "risk": _config.risk.__dict__,
        "execution": _config.execution.__dict__,
        "briefing": _config.briefing.__dict__,
        "journal_context": _config.journal_context.__dict__,
        "screener": _config.screener.__dict__,
        "llm": {
            "enabled": _config.llm.enabled,
            "primary_provider": _config.llm.resolved_primary(),
            "confidence_threshold": _config.llm.confidence_threshold,
            "timeout_seconds": _config.llm.timeout_seconds,
            "watchlist_interval_minutes": _config.llm.watchlist_interval_minutes,
            "google_model": _config.llm.google_model,
            "google_thinking_level": _config.llm.google_thinking_level,
            "google_rpm_limit": _config.llm.google_rpm_limit,
            "has_google_key": bool(_config.llm.google_api_key),
            "ollama_model": _config.llm.ollama_model,
            "openclaw_model": _config.llm.openclaw_model,
            "alert_channel": _config.llm.alert_channel,
        },
        "journal_db_path": _config.journal_db_path,
        "alpaca_base_url": _config.alpaca_base_url,
        "alpaca_data_feed": _config.alpaca_data_feed,
        "has_alpaca_keys": bool(_config.alpaca_api_key),
        "has_finnhub_key": bool(_config.finnhub_api_key),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "today": _today_et()}


@app.get("/api/overview")
def overview(date: str | None = None) -> dict[str, Any]:
    d = date or _today_et()
    summary = _journal.get_daily_summary(d)
    stats = _journal.get_stats(d)
    watchlist = _journal.get_daily_watchlist(d)
    return {
        "date": d,
        "summary": summary,
        "stats": stats,
        "watchlist": watchlist,
        "config": _sanitize_config(),
    }


@app.get("/api/trades")
def trades(
    date: str | None = None,
    symbol: str | None = None,
    limit: int = Query(200, le=500),
    offset: int = 0,
) -> list[dict[str, Any]]:
    return _journal.list_trades(date=date, symbol=symbol, limit=limit, offset=offset)


@app.get("/api/round-trips")
def round_trips(
    date: str | None = None,
    limit: int = Query(100, le=300),
) -> list[dict[str, Any]]:
    return _journal.get_round_trips(date=date, limit=limit)


@app.get("/api/signals")
def signals(
    date: str | None = None,
    symbol: str | None = None,
    signal_type: str | None = None,
    limit: int = Query(200, le=500),
    offset: int = 0,
) -> list[dict[str, Any]]:
    return _journal.list_signals(
        date=date,
        symbol=symbol,
        signal_type=signal_type,
        limit=limit,
        offset=offset,
    )


@app.get("/api/events")
def events(
    date: str | None = None,
    event_type: str | None = None,
    limit: int = Query(200, le=500),
    offset: int = 0,
) -> list[dict[str, Any]]:
    return _journal.list_events(
        date=date,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )


@app.get("/api/daily-pnl")
def daily_pnl(limit: int = Query(90, le=365)) -> list[dict[str, Any]]:
    return _journal.list_daily_pnl(limit=limit)


@app.get("/api/watchlist")
def watchlist(date: str | None = None) -> dict[str, Any]:
    d = date or _today_et()
    return {"date": d, "entries": _journal.get_daily_watchlist(d)}


@app.get("/api/watchlist/dates")
def watchlist_dates(limit: int = 30) -> list[str]:
    return _journal.list_watchlist_dates(limit=limit)


@app.get("/api/config")
def config() -> dict[str, Any]:
    return _sanitize_config()


@app.get("/api/logs")
def logs(lines: int = Query(200, le=1000)) -> dict[str, Any]:
    if not _log_path.exists():
        return {"path": str(_log_path), "lines": [], "exists": False}
    with open(_log_path) as f:
        tail = deque(f, maxlen=lines)
    return {
        "path": str(_log_path),
        "exists": True,
        "lines": [line.rstrip("\n") for line in tail],
    }


_frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


def main() -> None:
    import uvicorn

    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    uvicorn.run("src.api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
