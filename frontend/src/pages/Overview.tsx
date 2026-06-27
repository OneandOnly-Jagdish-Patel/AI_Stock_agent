import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import { StatCard } from "../components/StatCard";
import type { Overview } from "../types";
import { fmtMoney, fmtPct, fmtPctNum } from "../utils/format";

function marketBanner(status: string) {
  switch (status) {
    case "weekend":
      return "Market closed (weekend) — showing account balance and recent activity.";
    case "pre_market":
      return "Pre-market — session opens at 9:30 AM ET.";
    case "closed":
      return "Market closed for today — showing account balance and recent activity.";
    default:
      return null;
  }
}

export function OverviewPage() {
  const [date, setDate] = useState("");
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const o = await api.overview(date || undefined);
      setDate(o.date);
      setData(o);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  const equityChart = useMemo(() => {
    if (!data) return [];
    const history = [...(data.daily_pnl_history ?? [])].reverse();
    const points = history.map((r) => ({
      date: r.date.slice(5),
      equity: r.ending_equity,
      pnl: r.net_pnl,
    }));
    if (data.account?.equity != null) {
      const todayLabel = data.date.slice(5);
      const last = points[points.length - 1];
      if (!last || last.date !== todayLabel) {
        points.push({
          date: todayLabel,
          equity: data.account.equity,
          pnl: data.display_pnl ?? 0,
        });
      } else {
        last.equity = data.account.equity;
      }
    }
    return points;
  }, [data]);

  if (loading && !data) return <div className="loading">Loading dashboard…</div>;

  const stats = data?.stats;
  const account = data?.account;
  const lifetime = data?.lifetime_stats;
  const config = data?.config ?? {};
  const strategy = config.strategy as { mode?: string } | undefined;
  const swing = config.swing as {
    take_profit_pct?: number;
    stop_loss_pct?: number;
    max_hold_days?: number;
  } | undefined;
  const session = config.session as { start_time?: string } | undefined;
  const sessionEnd =
    (config.effective_session_end as string) ??
    (config.session as { end_time?: string })?.end_time ??
    "11:30";

  const dayPnl = data?.display_pnl ?? stats?.total_pnl;
  const hasDayActivity =
    (stats?.trade_count ?? 0) > 0 ||
    (stats?.entry_signals ?? 0) > 0 ||
    (dayPnl != null && dayPnl !== 0);

  const banner = data ? marketBanner(data.market_status) : null;
  const previousBalance =
    account?.previous_balance ??
    account?.last_equity ??
    data?.daily_pnl_history?.[0]?.ending_equity;

  return (
    <>
      <div className="page-header">
        <h2>Overview</h2>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button type="button" className="refresh-btn" onClick={load}>
            Refresh
          </button>
          <DateFilter value={date} onChange={setDate} />
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {banner && (
        <div
          className="panel"
          style={{ marginBottom: "1rem", padding: "0.75rem 1rem", opacity: 0.95 }}
        >
          {banner}
        </div>
      )}

      <div className="stats-grid">
        <StatCard
          label="Current Balance"
          value={account?.equity != null ? fmtMoney(account.equity) : "—"}
          sub={
            account?.available === false
              ? "Alpaca unavailable"
              : "Live from Alpaca"
          }
        />
        <StatCard
          label="Previous Balance"
          value={previousBalance != null ? fmtMoney(previousBalance) : "—"}
          sub="Prior day / last close"
        />
        <StatCard
          label="Change"
          value={
            account?.change != null
              ? fmtMoney(account.change)
              : previousBalance != null && account?.equity != null
                ? fmtMoney(account.equity - previousBalance)
                : "—"
          }
          className={
            (account?.change ?? 0) >= 0 ? "positive" : "negative"
          }
          sub={
            account?.change_pct != null
              ? fmtPctNum(account.change_pct)
              : undefined
          }
        />
        <StatCard
          label="Buying Power"
          value={
            account?.buying_power != null ? fmtMoney(account.buying_power) : "—"
          }
        />
      </div>

      <div className="stats-grid">
        <StatCard
          label={`P&L (${data?.date ?? "today"})`}
          value={
            hasDayActivity || dayPnl != null
              ? fmtMoney(dayPnl ?? 0)
              : "—"
          }
          className={(dayPnl ?? 0) >= 0 ? "positive" : "negative"}
          sub={
            hasDayActivity
              ? `${stats?.win_count ?? 0}W / ${stats?.loss_count ?? 0}L`
              : "No activity"
          }
        />
        <StatCard
          label="All-time P&L"
          value={fmtMoney(lifetime?.total_pnl ?? 0)}
          className={(lifetime?.total_pnl ?? 0) >= 0 ? "positive" : "negative"}
          sub={`${lifetime?.trade_count ?? 0} round trips`}
        />
        <StatCard
          label="Win Rate"
          value={
            (lifetime?.trade_count ?? 0) > 0
              ? fmtPct(lifetime?.win_rate)
              : hasDayActivity
                ? fmtPct(stats?.win_rate)
                : "—"
          }
          sub={
            (lifetime?.trade_count ?? 0) > 0
              ? `${lifetime?.win_count ?? 0}W / ${lifetime?.loss_count ?? 0}L lifetime`
              : "No closed trades yet"
          }
        />
        <StatCard
          label="Open Positions"
          value={String(data?.positions?.length ?? 0)}
          sub={
            data?.positions?.length
              ? data.positions.map((p) => p.symbol).join(", ")
              : "None"
          }
        />
      </div>

      {equityChart.length > 0 && (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          <div className="panel-header">Balance Over Time</div>
          <div className="panel-body chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#243044" />
                <XAxis dataKey="date" stroke="#8b9cb3" fontSize={12} />
                <YAxis
                  stroke="#8b9cb3"
                  fontSize={12}
                  domain={["auto", "auto"]}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#121820",
                    border: "1px solid #243044",
                    borderRadius: 8,
                  }}
                  formatter={(v: number, name: string) => [
                    name === "equity" ? fmtMoney(v) : fmtMoney(v),
                    name === "equity" ? "Equity" : "Daily P&L",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">Open Positions</div>
          <div className="panel-body data-table-wrap">
            {data?.positions?.length ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Unrealized</th>
                    <th>% Port</th>
                  </tr>
                </thead>
                <tbody>
                  {data.positions.map((p) => (
                    <tr key={p.symbol}>
                      <td>
                        <strong>{p.symbol}</strong>
                      </td>
                      <td className="mono">{p.qty}</td>
                      <td className="mono">{fmtMoney(p.avg_entry_price)}</td>
                      <td className="mono">{fmtMoney(p.current_price)}</td>
                      <td
                        className={`mono ${p.unrealized_pl >= 0 ? "positive" : "negative"}`}
                      >
                        {fmtMoney(p.unrealized_pl)} ({fmtPctNum(p.unrealized_plpc)})
                      </td>
                      <td className="mono">
                        {p.portfolio_pct != null ? `${p.portfolio_pct}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No open positions.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">Today&apos;s Watchlist</div>
          <div className="panel-body data-table-wrap">
            {data?.watchlist.length ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Source</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {data.watchlist.map((w) => (
                    <tr key={w.symbol}>
                      <td>
                        <strong>{w.symbol}</strong>
                      </td>
                      <td>
                        <span
                          className={`badge badge-${w.source === "anchor" ? "anchor" : "screener"}`}
                        >
                          {w.source}
                        </span>
                      </td>
                      <td className="reason-cell">{w.reason || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No screener data for this date.</div>
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">Agent Config</div>
        <div className="panel-body">
          <div className="trip-grid">
            <div>
              <dt>Mode</dt>
              <dd>{strategy?.mode ?? "—"}</dd>
            </div>
            <div>
              <dt>Session</dt>
              <dd>
                {session?.start_time}–{sessionEnd} ET
              </dd>
            </div>
            <div>
              <dt>LLM</dt>
              <dd>
                {(config.display_llm as string) ??
                  (config.llm as { display_llm?: string })?.display_llm ??
                  "—"}
              </dd>
            </div>
            <div>
              <dt>Screener</dt>
              <dd>
                {(config.screener as { mode?: string })?.mode ?? "—"}
              </dd>
            </div>
            {strategy?.mode === "swing" && swing && (
              <div>
                <dt>Swing targets</dt>
                <dd>
                  TP {swing.take_profit_pct}% · stop {swing.stop_loss_pct}% · max{" "}
                  {swing.max_hold_days}d
                </dd>
              </div>
            )}
            <div>
              <dt>Risk / Trade</dt>
              <dd>
                {(config.risk as { max_risk_per_trade_pct?: number })
                  ?.max_risk_per_trade_pct ?? "—"}
                %
              </dd>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
