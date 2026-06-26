import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import type { Signal } from "../types";
import { fmtTs } from "../utils/format";

const TYPES = [
  { value: "", label: "All signals" },
  { value: "entry", label: "Entries (approved)" },
  { value: "entry_vetoed", label: "Entries vetoed" },
  { value: "exit_advisor", label: "AI exit advisor" },
  { value: "exit", label: "Exits" },
];

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
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading signals…</div>}

      {!loading && (
        <div className="panel">
          <div className="panel-header">
            Signal log
            <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
              {signals.length} events
            </span>
          </div>
          <div className="panel-body data-table-wrap">
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
                      <span
                        className={`badge badge-${
                          s.signal_type === "entry_vetoed"
                            ? "veto"
                            : s.signal_type === "exit"
                              ? "exit"
                              : s.signal_type === "exit_advisor"
                                ? "screener"
                                : "entry"
                        }`}
                      >
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
                    <td className="reason-cell" style={{ color: "var(--purple)" }}>
                      {s.llm_reason || "—"}
                    </td>
                    <td className="mono">{s.rsi?.toFixed(1) ?? "—"}</td>
                    <td className="mono">
                      {s.vwap_dev != null ? `${s.vwap_dev.toFixed(3)}%` : "—"}
                    </td>
                    <td className="mono">{s.volume_ratio?.toFixed(2) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {signals.length === 0 && (
              <div className="empty">No signals for this filter.</div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
