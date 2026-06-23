import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { DateFilter } from "../components/DateFilter";
import type { Event } from "../types";
import { fmtTs } from "../utils/format";

const EVENT_TYPES = [
  "",
  "premarket_briefing",
  "watchlist_rank",
  "kill_switch",
];

export function EventsPage() {
  const [date, setDate] = useState("");
  const [eventType, setEventType] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const e = await api.events({
        date: date || undefined,
        event_type: eventType || undefined,
      });
      setEvents(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [date, eventType]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="page-header">
        <h2>Events &amp; Briefings</h2>
        <DateFilter value={date} onChange={setDate} />
      </div>

      <div className="filter-row">
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
        >
          <option value="">All events</option>
          {EVENT_TYPES.filter(Boolean).map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading events…</div>}

      {!loading && (
        <div className="panel">
          <div className="panel-header">
            Agent events
            <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
              {events.length} items
            </span>
          </div>
          <div className="panel-body">
            {events.length === 0 ? (
              <div className="empty">No events logged for this date.</div>
            ) : (
              events.map((e) => (
                <div className="trip-card" key={e.id}>
                  <div className="trip-header">
                    <span className={`badge badge-event`}>{e.event_type}</span>
                    <span className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                      {fmtTs(e.ts)}
                    </span>
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      fontFamily: "var(--font)",
                      fontSize: "0.88rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    {e.message}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
}
