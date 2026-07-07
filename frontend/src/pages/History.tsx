import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { ChartPanel } from "../components/ChartPanel";
import { EmptyState } from "../components/EmptyState";
import { HeroMetric } from "../components/HeroMetric";
import { LoadingButton } from "../components/LoadingButton";
import { PageSkeleton } from "../components/Skeleton";
import { StatCard } from "../components/StatCard";
import type { AccountSnapshot, DailySummary } from "../types";
import { chartTooltipStyle, getChartColors } from "../utils/chartTheme";
import { fmtMoney, fmtPctNum } from "../utils/format";

export function HistoryPage() {
  const [rows, setRows] = useState<DailySummary[]>([]);
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [chartColors, setChartColors] = useState(getChartColors());

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

  useEffect(() => {
    setChartColors(getChartColors());
  }, [rows, account]);

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
  const currentEquity = account?.equity ?? chartData.at(-1)?.equity ?? 0;
  const totalReturnPct =
    startEquity > 0 ? ((currentEquity - startEquity) / startEquity) * 100 : null;

  if (loading) return <PageSkeleton />;

  return (
    <>
      <div className="page-header">
        <h2>P&amp;L History</h2>
        <LoadingButton loading={loading} onClick={load}>
          Refresh
        </LoadingButton>
      </div>

      {error && <div className="error">{error}</div>}

      <HeroMetric
        label="Total P&L (all days)"
        value={fmtMoney(totalPnl)}
        positive={totalPnl >= 0}
        sub={`Current equity ${fmtMoney(currentEquity)}`}
      />

      <div className="metrics-scroll">
        <StatCard
          variant="compact"
          label="Current equity"
          value={fmtMoney(currentEquity)}
        />
        <StatCard variant="compact" label="Peak equity" value={fmtMoney(peakEquity)} />
        <StatCard
          variant="compact"
          label="Total return"
          value={totalReturnPct != null ? fmtPctNum(totalReturnPct) : "—"}
          className={(totalReturnPct ?? 0) >= 0 ? "positive" : "negative"}
        />
        <StatCard
          variant="compact"
          label="Trading days"
          value={String(rows.length)}
        />
      </div>

      {chartData.length > 0 && (
        <>
          <div className="panel">
            <div className="panel-header">Equity curve</div>
            <div className="panel-body chart-wrap chart-wrap--tall">
              <ChartPanel
                title="Equity curve"
                summary={`Portfolio equity from ${fmtMoney(startEquity)} to ${fmtMoney(currentEquity)} across ${chartData.length} data points.`}
              >
                <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="historyEquityGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={chartColors.positive} stopOpacity={0.25} />
                      <stop offset="100%" stopColor={chartColors.positive} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    stroke={chartColors.axis}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke={chartColors.axis}
                    fontSize={12}
                    domain={["auto", "auto"]}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                    width={52}
                  />
                  <Tooltip
                    contentStyle={chartTooltipStyle()}
                    formatter={(v: number) => [fmtMoney(v), "Equity"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke={chartColors.positive}
                    strokeWidth={2}
                    fill="url(#historyEquityGradient)"
                    dot={false}
                    activeDot={{ r: 4, fill: chartColors.positive }}
                  />
                </AreaChart>
              </ResponsiveContainer>
              </ChartPanel>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">Daily net P&amp;L</div>
            <div className="panel-body chart-wrap">
              <ChartPanel
                title="Daily net P&L"
                summary={`Daily profit and loss bars. Total cumulative P&L is ${fmtMoney(totalPnl)}.`}
              >
                <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis
                    dataKey="date"
                    stroke={chartColors.axis}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke={chartColors.axis}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    width={48}
                  />
                  <Tooltip
                    contentStyle={chartTooltipStyle()}
                    formatter={(v: number) => [fmtMoney(v), "P&L"]}
                  />
                  <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.pnl >= 0 ? chartColors.positive : chartColors.negative}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              </ChartPanel>
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
                    {r.net_pnl >= 0 ? "+" : ""}
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
            <EmptyState
              icon={BarChart3}
              title="No daily summaries yet"
              description="Run the agent during market hours to start tracking P&L history."
            />
          )}
        </div>
      </div>
    </>
  );
}
