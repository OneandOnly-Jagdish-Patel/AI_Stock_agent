import type { Position } from "../types";
import { fmtMoney, fmtPctNum } from "../utils/format";

interface Props {
  position: Position;
}

export function HoldingCard({ position: p }: Props) {
  const positive = p.unrealized_pl >= 0;
  return (
    <div className="holding-card">
      <div>
        <div className="holding-card-symbol">{p.symbol}</div>
        <div className="holding-card-meta">
          {p.qty} shares · avg {fmtMoney(p.avg_entry_price)}
        </div>
      </div>
      <div>
        <div className={`holding-card-pnl ${positive ? "positive" : "negative"}`}>
          {positive ? "+" : ""}
          {fmtMoney(p.unrealized_pl)}
        </div>
        <div
          className={`holding-card-pnl-pct ${positive ? "positive" : "negative"}`}
        >
          {fmtPctNum(p.unrealized_plpc)}
        </div>
      </div>
    </div>
  );
}
