import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import { StatCard } from "../components/StatCard";
import type { Overview } from "../types";
import { fmtMoney, fmtPct } from "../utils/format";

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

  if (loading && !data) return <div className="loading">Loading dashboard…</div>;

  const summary = data?.summary;
  const stats = data?.stats;

  return (
    <>
      <div className="page-header">
        <h2>Overview</h2>
        <DateFilter value={date} onChange={setDate} />
      </div>

      {error && <div className="error">{error}</div>}

      <div className="stats-grid">
        <StatCard
          label="Net P&L"
          value={fmtMoney(summary?.net_pnl ?? stats?.total_pnl ?? 0)}
          className={
            (summary?.net_pnl ?? stats?.total_pnl ?? 0) >= 0
              ? "positive"
              : "negative"
          }
          sub={summary ? `Equity ${fmtMoney(summary.ending_equity)}` : "Today"}
        />
        <StatCard
          label="Win Rate"
          value={fmtPct(stats?.win_rate ?? 0)}
          sub={`${stats?.win_count ?? 0}W / ${stats?.loss_count ?? 0}L`}
        />
        <StatCard
          label="Round Trips"
          value={stats?.trade_count ?? 0}
          sub="Completed sells"
        />
        <StatCard
          label="Entry Signals"
          value={stats?.entry_signals ?? 0}
          sub={`${stats?.llm_vetoes ?? 0} LLM vetoes`}
        />
        <StatCard
          label="Exits"
          value={stats?.exit_signals ?? 0}
          sub="Stop / TP / trail"
        />
        <StatCard
          label="Watchlist"
          value={data?.watchlist.length ?? 0}
          sub="Symbols today"
        />
      </div>

      <div className="grid-2">
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

        <div className="panel">
          <div className="panel-header">Agent Config</div>
          <div className="panel-body">
            <div className="trip-grid">
              <div>
                <dt>Session</dt>
                <dd>
                  {(data?.config.session as { start_time?: string })?.start_time}–
                  {(data?.config.session as { end_time?: string })?.end_time} ET
                </dd>
              </div>
              <div>
                <dt>Screener</dt>
                <dd>
                  {(data?.config.screener as { mode?: string })?.mode ?? "—"}
                </dd>
              </div>
              <div>
                <dt>LLM</dt>
                <dd>
                  {(data?.config.llm as { enabled?: boolean })?.enabled
                    ? (data?.config.llm as { ollama_model?: string })?.ollama_model
                    : "disabled"}
                </dd>
              </div>
              <div>
                <dt>Bracket Orders</dt>
                <dd>
                  {(data?.config.execution as { use_bracket_orders?: boolean })
                    ?.use_bracket_orders
                    ? "on"
                    : "off"}
                </dd>
              </div>
              <div>
                <dt>Max Spread</dt>
                <dd>
                  {(
                    (data?.config.execution as { max_spread_pct?: number })
                      ?.max_spread_pct ?? 0
                  ).toFixed(2)}
                  %
                </dd>
              </div>
              <div>
                <dt>Risk / Trade</dt>
                <dd>
                  {(data?.config.risk as { max_risk_per_trade_pct?: number })
                    ?.max_risk_per_trade_pct}
                  %
                </dd>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">Signal Activity</div>
        <div className="panel-body chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={[
                { name: "Entries", value: stats?.entry_signals ?? 0 },
                { name: "LLM Vetoes", value: stats?.llm_vetoes ?? 0 },
                { name: "Exits", value: stats?.exit_signals ?? 0 },
                { name: "Trades", value: stats?.trade_count ?? 0 },
              ]}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#243044" />
              <XAxis dataKey="name" stroke="#8b9cb3" fontSize={12} />
              <YAxis stroke="#8b9cb3" fontSize={12} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "#121820",
                  border: "1px solid #243044",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
