import { useCallback, useEffect, useState } from "react";
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
import type { DailySummary } from "../types";
import { fmtMoney } from "../utils/format";

export function HistoryPage() {
  const [rows, setRows] = useState<DailySummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRows(await api.dailyPnl());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const chartData = [...rows].reverse().map((r) => ({
    date: r.date.slice(5),
    pnl: r.net_pnl,
    equity: r.ending_equity,
    trades: r.trade_count,
    wins: r.win_count,
  }));

  const totalPnl = rows.reduce((s, r) => s + (r.net_pnl ?? 0), 0);

  return (
    <>
      <div className="page-header">
        <h2>P&amp;L History</h2>
        <button type="button" className="refresh-btn" onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading history…</div>}

      {!loading && (
        <>
          <div className="stats-grid" style={{ maxWidth: 480 }}>
            <div className="stat-card">
              <div className="label">Total P&amp;L (all days)</div>
              <div className={`value ${totalPnl >= 0 ? "positive" : "negative"}`}>
                {fmtMoney(totalPnl)}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">Trading days</div>
              <div className="value">{rows.length}</div>
            </div>
          </div>

          {chartData.length > 0 && (
            <div className="panel">
              <div className="panel-header">Daily net P&amp;L</div>
              <div className="panel-body chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#243044" />
                    <XAxis dataKey="date" stroke="#8b9cb3" fontSize={12} />
                    <YAxis stroke="#8b9cb3" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        background: "#121820",
                        border: "1px solid #243044",
                        borderRadius: 8,
                      }}
                      formatter={(v: number) => [fmtMoney(v), "P&L"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="pnl"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panel-header">Daily breakdown</div>
            <div className="panel-body data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Start equity</th>
                    <th>End equity</th>
                    <th>Net P&amp;L</th>
                    <th>Trades</th>
                    <th>Wins</th>
                    <th>Win rate</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.date}>
                      <td className="mono">{r.date}</td>
                      <td className="mono">{fmtMoney(r.starting_equity)}</td>
                      <td className="mono">{fmtMoney(r.ending_equity)}</td>
                      <td
                        className={`mono ${r.net_pnl >= 0 ? "positive" : "negative"}`}
                      >
                        {fmtMoney(r.net_pnl)}
                      </td>
                      <td className="mono">{r.trade_count}</td>
                      <td className="mono">{r.win_count}</td>
                      <td className="mono">
                        {r.trade_count
                          ? `${((r.win_count / r.trade_count) * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length === 0 && (
                <div className="empty">No daily summaries yet. Run the agent during market hours.</div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
