"""LLM router: Ollama primary, OpenClaw/Gemma fallback."""

from __future__ import annotations

import logging

from src.config import LLMConfig
from src.llm.ollama_client import OllamaClient, PremarketBriefing, ScreenerRanking, TradeVetoDecision, WatchlistRanking
from src.llm.openclaw_client import OpenClawClient

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.ollama = OllamaClient(config)
        self.openclaw = OpenClawClient(config)
        self._ollama_healthy: bool | None = None

    async def check_health(self) -> bool:
        self._ollama_healthy = await self.ollama.health_check()
        return self._ollama_healthy

    async def trade_veto(self, context: dict) -> tuple[TradeVetoDecision | None, str]:
        if not self.config.enabled:
            return TradeVetoDecision(action="approve", confidence=1.0, reason="llm_disabled"), "none"

        decision: TradeVetoDecision | None = None
        source = "none"

        if self._ollama_healthy is None:
            await self.check_health()

        if self._ollama_healthy:
            decision = await self.ollama.trade_veto(context)
            source = "ollama"

        if decision is None or decision.confidence < self.config.confidence_threshold:
            fallback = await self.openclaw.trade_veto(context)
            if fallback is not None:
                decision = fallback
                source = "openclaw"

        if decision is None:
            logger.info("LLM unavailable — fail-safe reject")
            return (
                TradeVetoDecision(action="reject", confidence=0.0, reason="llm_unavailable"),
                "fail_safe",
            )

        return decision, source

    async def rank_watchlist(self, context: dict) -> WatchlistRanking | None:
        if not self.config.enabled:
            return None

        ranking = await self.ollama.rank_watchlist(context)
        if ranking is not None:
            return ranking
        return await self.openclaw.rank_watchlist(context)

    async def briefing_decision(self, context: dict) -> PremarketBriefing:
        if self._ollama_healthy is None:
            await self.check_health()

        briefing: PremarketBriefing | None = None
        if self._ollama_healthy:
            briefing = await self.ollama.premarket_briefing(context)

        if briefing is None:
            briefing = await self.openclaw.premarket_briefing(context)

        if briefing is None:
            keyword_avoid = _keyword_avoid_list(context)
            return PremarketBriefing(
                avoid=keyword_avoid,
                caution=[],
                reason="LLM unavailable — using keyword-only detection",
            )

        return briefing

    async def screener_rank(self, context: dict) -> ScreenerRanking | None:
        if self._ollama_healthy is None:
            await self.check_health()

        ranking: ScreenerRanking | None = None
        if self._ollama_healthy:
            ranking = await self.ollama.screener_rank(context)

        if ranking is None or not ranking.picks:
            ranking = await self.openclaw.screener_rank(context)

        return ranking

    async def alert(self, title: str, message: str) -> None:
        await self.openclaw.send_alert(title, message)


def _keyword_avoid_list(context: dict) -> list[str]:
    flags = context.get("keyword_flags", {})
    return [sym for sym, hits in flags.items() if hits]
