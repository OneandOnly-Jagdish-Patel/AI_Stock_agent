import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import { PageSkeleton } from "../components/Skeleton";
import type { RoundTrip, Trade } from "../types";
import { fmtMoney, fmtTs } from "../utils/format";

const EXIT_LABELS: Record<string, string> = {
  stop_loss: "Stop loss hit",
  take_profit: "Take profit hit",
  trailing_stop: "Trailing stop",
  rsi_overbought: "RSI overbought",
  hard_stop: "Hard stop loss",
  entry_fill: "Entry filled",
  ai_exit_profit: "AI exit (profit)",
  ai_exit_loss: "AI exit (loss)",
  ai_exit_target_profit: "AI profit target hit",
  ai_exit_target_loss: "AI loss recovery target hit",
  ai_exit_timeout_profit: "AI profit hold timed out",
  ai_exit_timeout_loss: "AI loss hold timed out",
  swing_entry_fill: "Swing entry filled",
  ai_swing_exit_morning: "AI swing exit (morning review)",
};

function exitLabel(reason?: string) {
  if (!reason) return "—";
  return EXIT_LABELS[reason] ?? reason.replace(/_/g, " ");
}

export function TradesPage() {
  const [date, setDate] = useState("");
  const [dateInitialized, setDateInitialized] = useState(false);
  const [rounds, setRounds] = useState<RoundTrip[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"rounds" | "raw">("rounds");

  useEffect(() => {
    if (dateInitialized) return;
    api
      .lastTradeDate()
      .then((last) => {
        if (last) setDate(last);
        setDateInitialized(true);
      })
      .catch(() => setDateInitialized(true));
  }, [dateInitialized]);

  const load = useCallback(async () => {
    if (!dateInitialized) return;
    setLoading(true);
    setError("");
    try {
      const [r, t] = await Promise.all([
        api.roundTrips(date || undefined),
        api.trades({ date: date || undefined }),
      ]);
      setRounds(r);
      setTrades(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [date, dateInitialized]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !rounds.length && !trades.length) return <PageSkeleton />;

  return (
    <>
      <div className="page-header">
        <h2>Trades &amp; Reasons</h2>
        <div className="page-header-actions">
          <div className="segmented-control" role="group" aria-label="View mode">
            <button
              type="button"
              className={view === "rounds" ? "active" : ""}
              onClick={() => setView("rounds")}
            >
              Round trips
            </button>
            <button
              type="button"
              className={view === "raw" ? "active" : ""}
              onClick={() => setView("raw")}
            >
              Raw fills
            </button>
          </div>
          <DateFilter value={date} onChange={setDate} />
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {view === "rounds" && (
        <div className="panel">
          <div className="panel-header">
            Round Trips — entry → exit with reasons
            <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
              {rounds.length} trades
            </span>
          </div>
          <div className="panel-body">
            {rounds.length === 0 ? (
              <div className="empty">No completed round trips for this date.</div>
            ) : (
              rounds.map((r, i) => {
                const positive = (r.pnl ?? 0) >= 0;
                return (
                  <div className="insight-card" key={`${r.symbol}-${r.buy_ts}-${i}`}>
                    <div className="trip-header">
                      <span className="trip-symbol">{r.symbol}</span>
                      <span className={`pnl-badge ${positive ? "positive" : "negative"}`}>
                        {positive ? "+" : ""}
                        {fmtMoney(r.pnl)}
                      </span>
                    </div>
                    <dl className="trip-grid">
                      <div>
                        <dt>Buy</dt>
                        <dd>
                          {fmtTs(r.buy_ts)} @ {fmtMoney(r.buy_price)}
                        </dd>
                      </div>
                      <div>
                        <dt>Sell</dt>
                        <dd>
                          {r.sell_ts ? fmtTs(r.sell_ts) : "—"} @{" "}
                          {fmtMoney(r.sell_price)}
                        </dd>
                      </div>
                      <div>
                        <dt>Qty</dt>
                        <dd>{r.buy_qty}</dd>
                      </div>
                      <div>
                        <dt>RSI</dt>
                        <dd>{r.rsi?.toFixed(1) ?? "—"}</dd>
                      </div>
                      <div>
                        <dt>VWAP dev</dt>
                        <dd>
                          {r.vwap_dev != null ? `${r.vwap_dev.toFixed(3)}%` : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt>Vol ratio</dt>
                        <dd>{r.volume_ratio?.toFixed(2) ?? "—"}</dd>
                      </div>
                    </dl>
                    <div className="trip-reason">
                      <strong>Why bought</strong>
                      {r.entry_reason ?? "—"}
                    </div>
                    {r.llm_reason && (
                      <div className="trip-reason trip-reason--ai">
                        <strong>AI decision</strong>
                        {r.llm_action} ({((r.llm_confidence ?? 0) * 100).toFixed(0)}%) —{" "}
                        {r.llm_reason}
                      </div>
                    )}
                    <div className="trip-reason">
                      <strong>Why sold</strong>
                      {exitLabel(r.exit_reason)}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {view === "raw" && (
        <div className="panel">
          <div className="panel-header">All fills</div>
          <div className="panel-body data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Symbol</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>P&amp;L</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id}>
                    <td className="mono">{fmtTs(t.ts)}</td>
                    <td>
                      <span className={`badge badge-${t.side}`}>{t.side}</span>
                    </td>
                    <td>
                      <strong>{t.symbol}</strong>
                    </td>
                    <td className="mono">{t.qty}</td>
                    <td className="mono">{fmtMoney(t.price)}</td>
                    <td
                      className={`mono ${t.pnl != null ? (t.pnl >= 0 ? "positive" : "negative") : ""}`}
                    >
                      {t.pnl != null && t.pnl >= 0 ? "+" : ""}
                      {fmtMoney(t.pnl)}
                    </td>
                    <td className="reason-cell">{exitLabel(t.reason)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {trades.length === 0 && <div className="empty">No trades logged.</div>}
          </div>
        </div>
      )}
    </>
  );
}
