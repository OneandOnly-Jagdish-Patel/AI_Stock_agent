import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
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
};

function exitLabel(reason?: string) {
  if (!reason) return "—";
  return EXIT_LABELS[reason] ?? reason.replace(/_/g, " ");
}

export function TradesPage() {
  const [date, setDate] = useState("");
  const [rounds, setRounds] = useState<RoundTrip[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"rounds" | "raw">("rounds");

  const load = useCallback(async () => {
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
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="page-header">
        <h2>Trades &amp; Reasons</h2>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <div className="filter-row" style={{ margin: 0 }}>
            <select value={view} onChange={(e) => setView(e.target.value as "rounds" | "raw")}>
              <option value="rounds">Round trips (why sold)</option>
              <option value="raw">Raw fills</option>
            </select>
          </div>
          <DateFilter value={date} onChange={setDate} />
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading trades…</div>}

      {!loading && view === "rounds" && (
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
              rounds.map((r, i) => (
                <div className="trip-card" key={`${r.symbol}-${r.buy_ts}-${i}`}>
                  <div className="trip-header">
                    <span className="trip-symbol">{r.symbol}</span>
                    <span
                      className={`mono ${(r.pnl ?? 0) >= 0 ? "positive" : "negative"}`}
                      style={{ fontSize: "1.1rem", fontWeight: 600 }}
                    >
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
                    {r.llm_reason && (
                      <div style={{ marginTop: "0.35rem", color: "var(--purple)" }}>
                        AI: {r.llm_action} ({((r.llm_confidence ?? 0) * 100).toFixed(0)}%) —{" "}
                        {r.llm_reason}
                      </div>
                    )}
                  </div>
                  <div className="trip-reason">
                    <strong>Why sold</strong>
                    {exitLabel(r.exit_reason)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {!loading && view === "raw" && (
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
