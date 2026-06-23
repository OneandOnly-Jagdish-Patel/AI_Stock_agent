import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import type { WatchlistEntry } from "../types";

export function ScreenerPage() {
  const [date, setDate] = useState("");
  const [dates, setDates] = useState<string[]>([]);
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [availableDates, w] = await Promise.all([
        api.watchlistDates(),
        api.watchlist(date || undefined),
      ]);
      setDates(availableDates);
      if (!date) setDate(w.date);
      setEntries(w.entries);
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
        <h2>Daily Screener</h2>
        <DateFilter value={date} onChange={setDate} />
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading screener…</div>}

      {!loading && (
        <>
          <div className="panel">
            <div className="panel-header">
              Watchlist for {date}
              <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
                {entries.length} symbols
              </span>
            </div>
            <div className="panel-body">
              {entries.length === 0 ? (
                <div className="empty">
                  No screener run for this date. Agent runs screener at 8:45 AM ET.
                </div>
              ) : (
                entries.map((e) => (
                  <div className="trip-card" key={e.symbol}>
                    <div className="trip-header">
                      <span className="trip-symbol">{e.symbol}</span>
                      <span
                        className={`badge badge-${e.source === "anchor" ? "anchor" : "screener"}`}
                      >
                        {e.source}
                      </span>
                    </div>
                    <p className="reason-cell" style={{ margin: "0 0 0.75rem" }}>
                      {e.reason || "No reason recorded"}
                    </p>
                    {Object.keys(e.metrics).length > 0 && (
                      <dl className="trip-grid">
                        {Object.entries(e.metrics).map(([k, v]) => (
                          <div key={k}>
                            <dt>{k}</dt>
                            <dd>{typeof v === "number" ? v.toFixed(2) : v}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {dates.length > 1 && (
            <div className="panel">
              <div className="panel-header">Screener history</div>
              <div className="panel-body data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dates.map((d) => (
                      <tr key={d}>
                        <td className="mono">{d}</td>
                        <td>
                          <button
                            type="button"
                            className="refresh-btn"
                            style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
                            onClick={() => setDate(d)}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
