"""Google AI Studio / Gemini API client for structured LLM tasks."""

from __future__ import annotations

import asyncio
import json
import logging
import time

import aiohttp

from src.config import LLMConfig
from src.llm.ollama_client import (
    ExitAdvisorDecision,
    OllamaClient,
    PremarketBriefing,
    ScreenerRanking,
    TradeVetoDecision,
    WatchlistRanking,
)
from src.llm.prompts import (
    EXIT_ADVISOR_PROMPT,
    PREMARKET_BRIEFING_PROMPT,
    SCREENER_RANK_PROMPT,
    TRADE_VETO_PROMPT,
    WATCHLIST_RANK_PROMPT,
)

logger = logging.getLogger(__name__)

_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GoogleClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.api_key = config.google_api_key
        self.model = config.google_model
        self._last_request_at: float = 0.0
        self._rate_lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _generation_config(self) -> dict:
        config: dict = {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        }
        level = self.config.google_thinking_level.strip()
        if level and level.lower() not in ("off", "none", "disabled"):
            config["thinkingConfig"] = {"thinkingLevel": level.upper()}
        return config

    async def _rate_limit(self) -> None:
        rpm = self.config.google_rpm_limit
        if rpm <= 0:
            return
        min_interval = 60.0 / rpm
        async with self._rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - self._last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def _generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        await self._rate_limit()

        url = f"{_GOOGLE_API_BASE}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": self._generation_config(),
        }
        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=15,
            sock_read=self.config.timeout_seconds,
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=timeout,
            ) as resp:
                if resp.status == 429:
                    raise aiohttp.ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=429,
                        message="Google API rate limit (429)",
                    )
                resp.raise_for_status()
                data = await resp.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise ValueError("Google API returned no candidates")
        return self._extract_response_text(candidates[0])

    @staticmethod
    def _extract_response_text(candidate: dict) -> str:
        """Return model output, skipping Gemma 4 internal thought parts."""
        parts = candidate.get("content", {}).get("parts") or []
        if not parts:
            raise ValueError("Google API returned empty content")

        for part in reversed(parts):
            if part.get("thought"):
                continue
            text = part.get("text", "")
            if text:
                return text

        for part in reversed(parts):
            text = part.get("text", "")
            if text:
                return text

        raise ValueError("Google API returned empty content")

    async def trade_veto(self, context: dict) -> TradeVetoDecision | None:
        prompt = TRADE_VETO_PROMPT.format(context=json.dumps(context, indent=2))
        for attempt in range(2):
            try:
                raw = await self._generate(prompt)
                parsed = OllamaClient._extract_json(raw)
                return TradeVetoDecision.model_validate(parsed)
            except Exception as e:
                logger.warning(
                    "Google trade_veto attempt %d failed: %s: %s",
                    attempt + 1,
                    type(e).__name__,
                    e or "(no message)",
                )
        return None

    async def rank_watchlist(self, context: dict) -> WatchlistRanking | None:
        prompt = WATCHLIST_RANK_PROMPT.format(context=json.dumps(context, indent=2))
        try:
            raw = await self._generate(prompt)
            parsed = OllamaClient._extract_json(raw)
            return WatchlistRanking.model_validate(parsed)
        except Exception as e:
            logger.warning("Google rank_watchlist failed: %s: %s", type(e).__name__, e or "(no message)")
            return None

    async def premarket_briefing(self, context: dict) -> PremarketBriefing | None:
        prompt = PREMARKET_BRIEFING_PROMPT.format(
            symbols=", ".join(context.get("symbols", [])),
            news=json.dumps(context.get("news", []), indent=2),
            keyword_flags=json.dumps(context.get("keyword_flags", {}), indent=2),
        )
        try:
            raw = await self._generate(prompt)
            parsed = OllamaClient._extract_json(raw)
            return PremarketBriefing.model_validate(parsed)
        except Exception as e:
            logger.warning("Google premarket_briefing failed: %s: %s", type(e).__name__, e or "(no message)")
            return None

    @staticmethod
    def _trim_screener_context(context: dict) -> dict:
        trimmed: list[dict] = []
        for c in context.get("candidates", []):
            row = dict(c)
            headline = row.get("headline")
            if isinstance(headline, str) and len(headline) > 120:
                row["headline"] = headline[:117] + "..."
            trimmed.append(row)
        return {**context, "candidates": trimmed}

    async def screener_rank(self, context: dict) -> ScreenerRanking | None:
        trimmed = self._trim_screener_context(context)
        prompt = SCREENER_RANK_PROMPT.format(
            slots=trimmed.get("slots", 3),
            candidates=json.dumps(trimmed.get("candidates", []), indent=2),
        )
        for attempt in range(2):
            try:
                raw = await self._generate(prompt)
                parsed = OllamaClient._extract_json(raw)
                return ScreenerRanking.model_validate(parsed)
            except (asyncio.TimeoutError, TimeoutError) as e:
                logger.warning(
                    "Google screener_rank attempt %d timed out after %ss",
                    attempt + 1,
                    self.config.timeout_seconds,
                )
                if attempt == 0:
                    continue
                return None
            except Exception as e:
                logger.warning("Google screener_rank failed: %s: %s", type(e).__name__, e or "(no message)")
                return None
        return None

    async def exit_advisor(self, context: dict) -> ExitAdvisorDecision | None:
        ai_exit = context.get("_ai_exit_limits", {})
        prompt = EXIT_ADVISOR_PROMPT.format(
            zone=context.get("zone", "profit"),
            hard_stop_pct=ai_exit.get("hard_stop_loss_pct", 0.12),
            context=json.dumps({k: v for k, v in context.items() if not k.startswith("_")}, indent=2),
            min_take_profit_pct=ai_exit.get("min_take_profit_pct", 0.20),
            max_target_pct=ai_exit.get("max_target_pct", 1.0),
            max_hold_minutes=ai_exit.get("max_hold_minutes", 20),
            max_loss_hold_minutes=ai_exit.get("max_loss_hold_minutes", 8),
        )
        try:
            raw = await self._generate(prompt)
            parsed = OllamaClient._extract_json(raw)
            return ExitAdvisorDecision.model_validate(parsed)
        except Exception as e:
            logger.warning("Google exit_advisor failed: %s: %s", type(e).__name__, e or "(no message)")
            return None
