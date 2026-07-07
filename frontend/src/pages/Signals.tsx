import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DataTable } from "../components/DataTable";
import { DateFilter } from "../components/DateFilter";
import { PageSkeleton } from "../components/Skeleton";
import type { Signal } from "../types";
import { fmtTs } from "../utils/format";

const TYPES = [
  { value: "", label: "All signals" },
  { value: "entry", label: "Entries (approved)" },
  { value: "entry_vetoed", label: "Entries vetoed" },
  { value: "exit_advisor", label: "AI exit advisor" },
  { value: "swing_review", label: "Swing morning review" },
  { value: "exit", label: "Exits" },
];

function signalBadgeClass(type: string) {
  if (type === "entry_vetoed") return "veto";
  if (type === "exit") return "exit";
  if (type === "exit_advisor") return "screener";
  return "entry";
}

function SignalMobileCard({ s }: { s: Signal }) {
  return (
    <div className="signal-card">
      <div className="signal-card-header">
        <div>
          <strong>{s.symbol}</strong>
          <div className="mono" style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
            {fmtTs(s.ts)}
          </div>
        </div>
        <span className={`badge badge-${signalBadgeClass(s.signal_type)}`}>
          {s.signal_type}
        </span>
      </div>
      {s.details && <div className="signal-card-reason">{s.details}</div>}
      {s.llm_reason && (
        <div className="signal-card-ai">
          {s.llm_action} ({((s.llm_confidence ?? 0) * 100).toFixed(0)}%) — {s.llm_reason}
        </div>
      )}
    </div>
  );
}

export function SignalsPage() {
  const [date, setDate] = useState("");
  const [signalType, setSignalType] = useState("");
  const [signals, setSignals] = useState<Signal[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.signals({
        date: date || undefined,
        signal_type: signalType || undefined,
      });
      setSignals(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [date, signalType]);

  useEffect(() => {
    load();
  }, [load]);

  const tableDesktop = (
    <table className="data-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Symbol</th>
          <th>Type</th>
          <th>Rule reason</th>
          <th>LLM</th>
          <th>Confidence</th>
          <th>AI reason</th>
          <th>RSI</th>
          <th>VWAP</th>
          <th>Vol</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((s) => (
          <tr key={s.id}>
            <td className="mono">{fmtTs(s.ts)}</td>
            <td>
              <strong>{s.symbol}</strong>
            </td>
            <td>
              <span className={`badge badge-${signalBadgeClass(s.signal_type)}`}>
                {s.signal_type}
              </span>
            </td>
            <td className="reason-cell">{s.details || "—"}</td>
            <td>{s.llm_action ?? "—"}</td>
            <td className="mono">
              {s.llm_confidence != null
                ? `${(s.llm_confidence * 100).toFixed(0)}%`
                : "—"}
            </td>
            <td className="reason-cell ai-text">{s.llm_reason || "—"}</td>
            <td className="mono">{s.rsi?.toFixed(1) ?? "—"}</td>
            <td className="mono">
              {s.vwap_dev != null ? `${s.vwap_dev.toFixed(3)}%` : "—"}
            </td>
            <td className="mono">{s.volume_ratio?.toFixed(2) ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const tableMobile = (
    <div>
      {signals.map((s) => (
        <SignalMobileCard key={s.id} s={s} />
      ))}
    </div>
  );

  if (loading && !signals.length) return <PageSkeleton />;

  return (
    <>
      <div className="page-header">
        <h2>AI Decisions &amp; Signals</h2>
        <DateFilter value={date} onChange={setDate} />
      </div>

      <div className="filter-row">
        <select
          value={signalType}
          onChange={(e) => setSignalType(e.target.value)}
          aria-label="Filter by signal type"
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="panel">
        <div className="panel-header">
          Signal log
          <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
            {signals.length} events
          </span>
        </div>
        <div className="panel-body panel-body--flush data-table-wrap">
          {signals.length === 0 ? (
            <div className="empty">No signals for this filter.</div>
          ) : (
            <DataTable desktop={tableDesktop} mobile={tableMobile} />
          )}
        </div>
      </div>
    </>
  );
}
