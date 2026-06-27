import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { AccountSnapshot, DailySummary } from "../types";
import { fmtMoney, fmtPctNum } from "../utils/format";

export function HistoryPage() {
  const [rows, setRows] = useState<DailySummary[]>([]);
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [daily, acct] = await Promise.all([
        api.dailyPnl(),
        api.account(),
      ]);
      setRows(daily);
      setAccount(acct);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const chartData = useMemo(() => {
    const base = [...rows].reverse().map((r) => ({
      date: r.date.slice(5),
      fullDate: r.date,
      pnl: r.net_pnl,
      equity: r.ending_equity,
    }));
    if (account?.equity != null && base.length > 0) {
      const today = new Date().toISOString().slice(0, 10);
      const last = base[base.length - 1];
      if (last.fullDate !== today) {
        base.push({
          date: today.slice(5),
          fullDate: today,
          pnl: 0,
          equity: account.equity,
        });
      } else {
        last.equity = account.equity;
      }
    }
    return base;
  }, [rows, account]);

  const totalPnl = rows.reduce((s, r) => s + (r.net_pnl ?? 0), 0);
  const peakEquity = Math.max(
    ...chartData.map((r) => r.equity),
    account?.equity ?? 0,
  );
  const startEquity =
    chartData.length > 0 ? chartData[0].equity : account?.equity ?? 0;
  const currentEquity = account?.equity ?? (chartData.at(-1)?.equity ?? 0);
  const totalReturnPct =
    startEquity > 0 ? ((currentEquity - startEquity) / startEquity) * 100 : null;

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
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Current equity</div>
              <div className="value">{fmtMoney(currentEquity)}</div>
            </div>
            <div className="stat-card">
              <div className="label">Peak equity</div>
              <div className="value">{fmtMoney(peakEquity)}</div>
            </div>
            <div className="stat-card">
              <div className="label">Total P&amp;L (all days)</div>
              <div className={`value ${totalPnl >= 0 ? "positive" : "negative"}`}>
                {fmtMoney(totalPnl)}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">Total return</div>
              <div
                className={`value ${(totalReturnPct ?? 0) >= 0 ? "positive" : "negative"}`}
              >
                {totalReturnPct != null ? fmtPctNum(totalReturnPct) : "—"}
              </div>
            </div>
          </div>

          {chartData.length > 0 && (
            <>
              <div className="panel">
                <div className="panel-header">Equity curve</div>
                <div className="panel-body chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
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
                        formatter={(v: number) => [fmtMoney(v), "Equity"]}
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

              <div className="panel">
                <div className="panel-header">Daily net P&amp;L</div>
                <div className="panel-body chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
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
                      <Bar dataKey="pnl" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
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
                <div className="empty">
                  No daily summaries yet. Run the agent during market hours.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
