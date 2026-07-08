"""Restore agent state from Alpaca-held positions after restart."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.strategy.swing_scalper import SwingScalper, SwingState

if TYPE_CHECKING:
    from src.data.bars import BarManager
    from src.execution.positions import PositionManager
    from src.journal.logger import TradeJournal

logger = logging.getLogger(__name__)


def held_symbols(positions: PositionManager) -> list[str]:
    """Symbols with a long Alpaca position."""
    try:
        return [
            str(pos.symbol).upper()
            for pos in positions.list_positions()
            if float(pos.qty) > 0
        ]
    except Exception:
        logger.warning("Failed to list Alpaca positions", exc_info=True)
        return []


def _parse_entry_time(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


async def hydrate_swing_positions(
    positions: PositionManager,
    scalpers: dict[str, SwingScalper],
    journal: TradeJournal,
    bar_manager: BarManager,
) -> list[str]:
    """Sync Alpaca holdings into swing scalpers and run immediate stop checks."""
    hydrated: list[str] = []

    for pos in positions.list_positions():
        qty = float(pos.qty)
        if qty <= 0:
            continue

        symbol = str(pos.symbol).upper()
        scalper = scalpers.get(symbol)
        if not isinstance(scalper, SwingScalper):
            logger.warning("%s held at Alpaca but has no swing scalper — skipping hydration", symbol)
            continue

        if scalper.state == SwingState.IN_POSITION:
            logger.debug("%s already IN_POSITION — skipping hydration", symbol)
            continue

        entry_price = float(pos.avg_entry_price)
        current_price = float(pos.current_price)
        lot = journal.get_open_lot(symbol)
        entry_time = _parse_entry_time(lot["ts"] if lot else None)

        scalper.hydrate_from_alpaca(
            entry_price=entry_price,
            qty=qty,
            current_price=current_price,
            entry_time=entry_time,
        )

        pnl_pct = scalper._pnl_pct(current_price)
        journal.log_event(
            "position_hydrated",
            f"{symbol} qty={qty} entry={entry_price:.2f} current={current_price:.2f} pnl={pnl_pct:.2f}%",
        )

        indicator_state = bar_manager.states.get(symbol)
        if await scalper.check_hydration_exit(current_price, indicator_state):
            logger.info("%s catch-up exit submitted after hydration (pnl=%.2f%%)", symbol, pnl_pct)
        else:
            hydrated.append(symbol)

    if hydrated:
        logger.info("Hydrated open positions: %s", ", ".join(hydrated))
    return hydrated
