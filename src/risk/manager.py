"""Hard-coded risk limits — never delegated to LLM."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from src.config import AppConfig
from src.execution.positions import PositionManager

logger = logging.getLogger(__name__)


@dataclass
class RiskState:
    starting_equity: float = 0.0
    current_equity: float = 0.0
    day_trade_count: int = 0
    kill_switch: bool = False
    kill_reason: str = ""
    session_date: date | None = None
    realized_pnl_today: float = 0.0
    open_symbols: set[str] = field(default_factory=set)


class RiskManager:
    def __init__(self, config: AppConfig, positions: PositionManager) -> None:
        self.config = config
        self.positions = positions
        self.state = RiskState()

    def reset_session(self, equity: float, today: date) -> None:
        if self.state.session_date != today:
            self.state = RiskState(
                starting_equity=equity,
                current_equity=equity,
                session_date=today,
            )
            logger.info("Risk session reset: equity=%.2f date=%s", equity, today)

    def update_equity(self, equity: float) -> None:
        self.state.current_equity = equity
        self._check_daily_loss()

    def record_day_trade(self) -> None:
        self.state.day_trade_count += 1

    def record_realized_pnl(self, pnl: float) -> None:
        self.state.realized_pnl_today += pnl
        self._check_daily_loss()

    def _check_daily_loss(self) -> None:
        if self.state.starting_equity <= 0:
            return
        loss_pct = (
            (self.state.starting_equity - self.state.current_equity)
            / self.state.starting_equity
        ) * 100
        if loss_pct >= self.config.risk.daily_max_loss_pct:
            self.trigger_kill_switch(
                f"Daily max loss reached: {loss_pct:.2f}% >= {self.config.risk.daily_max_loss_pct}%"
            )

    def trigger_kill_switch(self, reason: str) -> None:
        if not self.state.kill_switch:
            logger.warning("KILL SWITCH: %s", reason)
        self.state.kill_switch = True
        self.state.kill_reason = reason

    def can_open_position(self, symbol: str) -> tuple[bool, str]:
        if self.state.kill_switch:
            return False, f"kill_switch: {self.state.kill_reason}"

        open_count = self.positions.open_position_count()
        if open_count >= self.config.risk.max_open_positions:
            return False, f"max_open_positions ({self.config.risk.max_open_positions})"

        if symbol in self.state.open_symbols:
            return False, "already_in_position"

        equity = self.state.current_equity
        if equity < self.config.risk.pdt_equity_threshold:
            if self.state.day_trade_count >= self.config.risk.max_day_trades:
                return False, (
                    f"pdt_guard: {self.state.day_trade_count} day trades "
                    f"(max {self.config.risk.max_day_trades} under ${self.config.risk.pdt_equity_threshold:.0f})"
                )

        return True, "ok"

    def register_open(self, symbol: str) -> None:
        self.state.open_symbols.add(symbol)

    def register_close(self, symbol: str) -> None:
        self.state.open_symbols.discard(symbol)
        self.record_day_trade()

    def is_killed(self) -> bool:
        return self.state.kill_switch
