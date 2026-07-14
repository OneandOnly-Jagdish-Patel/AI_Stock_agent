"""Regression: live subscribe/unsubscribe must not deadlock the event loop."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data.stream import MarketDataStream


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        alpaca_api_key="PK_TEST",
        alpaca_secret_key="SECRET",
        alpaca_data_feed="iex",
    )


@pytest.mark.asyncio
async def test_subscribe_while_running_awaits_send_without_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    send = AsyncMock()
    fake_stream = MagicMock()
    fake_stream._handlers = {"bars": {}, "quotes": {}}
    fake_stream._running = True
    fake_stream._loop = asyncio.get_running_loop()
    fake_stream._ensure_coroutine = MagicMock()
    fake_stream._send_subscribe_msg = send
    fake_stream._send_unsubscribe_msg = AsyncMock()
    fake_stream._should_run = True
    fake_stream._stop_stream_queue = MagicMock()
    fake_stream._stop_stream_queue.empty.return_value = True

    monkeypatch.setattr("src.data.stream.StockDataStream", lambda **kwargs: fake_stream)
    monkeypatch.setattr("src.data.stream._parse_feed", lambda feed: feed)

    async def on_bar(symbol: str, data: dict) -> None:
        return None

    stream = MarketDataStream(_config(), ["AAPL"], on_bar=on_bar)  # type: ignore[arg-type]

    # Must complete on the same loop (old Alpaca .result() path deadlocked here).
    await asyncio.wait_for(stream.subscribe(["RIVN"]), timeout=1.0)

    assert "RIVN" in stream.symbols
    assert "RIVN" in fake_stream._handlers["bars"]
    assert "RIVN" in fake_stream._handlers["quotes"]
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsubscribe_while_running_awaits_send(monkeypatch: pytest.MonkeyPatch) -> None:
    unsub = AsyncMock()
    fake_stream = MagicMock()
    fake_stream._handlers = {"bars": {}, "quotes": {}}
    fake_stream._running = True
    fake_stream._loop = asyncio.get_running_loop()
    fake_stream._ensure_coroutine = MagicMock()
    fake_stream._send_subscribe_msg = AsyncMock()
    fake_stream._send_unsubscribe_msg = unsub
    fake_stream._should_run = True
    fake_stream._stop_stream_queue = MagicMock()
    fake_stream._stop_stream_queue.empty.return_value = True

    monkeypatch.setattr("src.data.stream.StockDataStream", lambda **kwargs: fake_stream)
    monkeypatch.setattr("src.data.stream._parse_feed", lambda feed: feed)

    async def on_bar(symbol: str, data: dict) -> None:
        return None

    stream = MarketDataStream(_config(), ["AAPL", "RIVN"], on_bar=on_bar)  # type: ignore[arg-type]
    await asyncio.wait_for(stream.unsubscribe(["RIVN"]), timeout=1.0)

    assert "RIVN" not in stream.symbols
    assert "RIVN" not in fake_stream._handlers["bars"]
    assert unsub.await_count == 2  # bars + quotes


@pytest.mark.asyncio
async def test_stop_on_same_loop_does_not_call_blocking_sdk_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_stream = MagicMock()
    fake_stream._handlers = {"bars": {}, "quotes": {}}
    fake_stream._running = True
    fake_stream._loop = asyncio.get_running_loop()
    fake_stream._ensure_coroutine = MagicMock()
    fake_stream._should_run = True
    fake_stream._stop_stream_queue = MagicMock()
    fake_stream._stop_stream_queue.empty.return_value = True

    monkeypatch.setattr("src.data.stream.StockDataStream", lambda **kwargs: fake_stream)
    monkeypatch.setattr("src.data.stream._parse_feed", lambda feed: feed)

    async def on_bar(symbol: str, data: dict) -> None:
        return None

    stream = MarketDataStream(_config(), ["AAPL"], on_bar=on_bar)  # type: ignore[arg-type]
    stream.stop()

    fake_stream.stop.assert_not_called()
    assert fake_stream._should_run is False
    fake_stream._stop_stream_queue.put_nowait.assert_called_once()
