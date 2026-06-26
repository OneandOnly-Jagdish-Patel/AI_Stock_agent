"""LLM router: Google AI Studio primary (optional), Ollama fallback, OpenClaw alerts."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from src.config import LLMConfig
from src.llm.google_client import GoogleClient
from src.llm.ollama_client import (
    ExitAdvisorDecision,
    OllamaClient,
    PremarketBriefing,
    ScreenerRanking,
    TradeVetoDecision,
    WatchlistRanking,
)
from src.llm.openclaw_client import OpenClawClient

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.google = GoogleClient(config)
        self.ollama = OllamaClient(config)
        self.openclaw = OpenClawClient(config)
        self._ollama_healthy: bool | None = None
        self._primary = config.resolved_primary()

    async def check_health(self) -> bool:
        self._ollama_healthy = await self.ollama.health_check()
        if self._primary == "google" and self.google.configured:
            return True
        return bool(self._ollama_healthy)

    def _provider_chain(self) -> list[tuple[str, bool]]:
        """Ordered list of (name, is_available) for LLM providers."""
        chain: list[tuple[str, bool]] = []
        if self._primary == "google" and self.google.configured:
            chain.append(("google", True))
            chain.append(("ollama", self._ollama_healthy is True))
            chain.append(("openclaw", True))
        else:
            if self._ollama_healthy is None:
                pass  # caller should run check_health first
            chain.append(("ollama", self._ollama_healthy is not False))
            if self.google.configured:
                chain.append(("google", True))
            chain.append(("openclaw", True))
        return chain

    async def _first_result(
        self,
        fns: dict[str, Callable[[], Awaitable[object | None]]],
    ) -> tuple[object | None, str]:
        for name, available in self._provider_chain():
            if not available or name not in fns:
                continue
            result = await fns[name]()
            if result is not None:
                return result, name
        return None, "none"

    async def trade_veto(self, context: dict) -> tuple[TradeVetoDecision | None, str]:
        if not self.config.enabled:
            return TradeVetoDecision(action="approve", confidence=1.0, reason="llm_disabled"), "none"

        if self._ollama_healthy is None and self._primary != "google":
            await self.check_health()

        fns = {
            "google": lambda: self.google.trade_veto(context),
            "ollama": lambda: self.ollama.trade_veto(context),
            "openclaw": lambda: self.openclaw.trade_veto(context),
        }

        best: TradeVetoDecision | None = None
        best_source = "none"

        for name, available in self._provider_chain():
            if not available or name not in fns:
                continue
            decision = await fns[name]()
            if decision is None:
                continue
            if decision.confidence >= self.config.confidence_threshold:
                return decision, name
            if best is None or decision.confidence > best.confidence:
                best = decision
                best_source = name

        if best is not None:
            return best, best_source

        logger.info("LLM unavailable — fail-safe reject")
        return (
            TradeVetoDecision(action="reject", confidence=0.0, reason="llm_unavailable"),
            "fail_safe",
        )

    async def rank_watchlist(self, context: dict) -> WatchlistRanking | None:
        if not self.config.enabled:
            return None
        if self._ollama_healthy is None and self._primary != "google":
            await self.check_health()
        result, _ = await self._first_result(
            {
                "google": lambda: self.google.rank_watchlist(context),
                "ollama": lambda: self.ollama.rank_watchlist(context),
                "openclaw": lambda: self.openclaw.rank_watchlist(context),
            }
        )
        return result  # type: ignore[return-value]

    async def briefing_decision(self, context: dict) -> PremarketBriefing:
        if self._ollama_healthy is None and self._primary != "google":
            await self.check_health()
        briefing, _ = await self._first_result(
            {
                "google": lambda: self.google.premarket_briefing(context),
                "ollama": lambda: self.ollama.premarket_briefing(context),
                "openclaw": lambda: self.openclaw.premarket_briefing(context),
            }
        )
        if briefing is not None:
            return briefing  # type: ignore[return-value]

        return PremarketBriefing(
            avoid=_keyword_avoid_list(context),
            caution=[],
            reason="LLM unavailable — using keyword-only detection",
        )

    async def screener_rank(self, context: dict) -> ScreenerRanking | None:
        if self._ollama_healthy is None and self._primary != "google":
            await self.check_health()
        result, _ = await self._first_result(
            {
                "google": lambda: self.google.screener_rank(context),
                "ollama": lambda: self.ollama.screener_rank(context),
                "openclaw": lambda: self.openclaw.screener_rank(context),
            }
        )
        return result  # type: ignore[return-value]

    async def exit_advisor(self, context: dict) -> tuple[ExitAdvisorDecision, str]:
        """Fail-safe: sell if LLM unavailable or low confidence."""
        sell = ExitAdvisorDecision(action="sell", confidence=0.0, reason="llm_unavailable_fail_safe")

        if not self.config.enabled:
            return sell, "none"

        if self._ollama_healthy is None and self._primary != "google":
            await self.check_health()

        result, source = await self._first_result(
            {
                "google": lambda: self.google.exit_advisor(context),
                "ollama": lambda: self.ollama.exit_advisor(context),
                "openclaw": lambda: self.openclaw.exit_advisor(context),
            }
        )
        if result is None:
            logger.info("LLM exit_advisor unavailable — fail-safe sell")
            return sell, "fail_safe"

        decision = result  # type: ignore[assignment]
        if decision.confidence < self.config.confidence_threshold:
            return (
                ExitAdvisorDecision(
                    action="sell",
                    confidence=decision.confidence,
                    reason=f"low_confidence: {decision.reason}",
                ),
                source,
            )
        return decision, source

    async def alert(self, title: str, message: str) -> None:
        await self.openclaw.send_alert(title, message)


def _keyword_avoid_list(context: dict) -> list[str]:
    flags = context.get("keyword_flags", {})
    return [sym for sym, hits in flags.items() if hits]
