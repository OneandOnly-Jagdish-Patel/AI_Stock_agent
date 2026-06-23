import type {
  DailySummary,
  Event,
  Overview,
  RoundTrip,
  Signal,
  Trade,
  WatchlistEntry,
} from "../types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  overview: (date?: string) =>
    get<Overview>(`/api/overview${date ? `?date=${date}` : ""}`),
  trades: (params?: { date?: string; symbol?: string }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set("date", params.date);
    if (params?.symbol) q.set("symbol", params.symbol);
    const qs = q.toString();
    return get<Trade[]>(`/api/trades${qs ? `?${qs}` : ""}`);
  },
  roundTrips: (date?: string) =>
    get<RoundTrip[]>(`/api/round-trips${date ? `?date=${date}` : ""}`),
  signals: (params?: { date?: string; signal_type?: string }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set("date", params.date);
    if (params?.signal_type) q.set("signal_type", params.signal_type);
    const qs = q.toString();
    return get<Signal[]>(`/api/signals${qs ? `?${qs}` : ""}`);
  },
  events: (params?: { date?: string; event_type?: string }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set("date", params.date);
    if (params?.event_type) q.set("event_type", params.event_type);
    const qs = q.toString();
    return get<Event[]>(`/api/events${qs ? `?${qs}` : ""}`);
  },
  dailyPnl: () => get<DailySummary[]>("/api/daily-pnl"),
  watchlist: (date?: string) =>
    get<{ date: string; entries: WatchlistEntry[] }>(
      `/api/watchlist${date ? `?date=${date}` : ""}`,
    ),
  watchlistDates: () => get<string[]>("/api/watchlist/dates"),
  logs: (lines = 200) => get<{ lines: string[]; exists: boolean }>(`/api/logs?lines=${lines}`),
  config: () => get<Record<string, unknown>>("/api/config"),
};
