export interface DailySummary {
  date: string;
  starting_equity: number;
  ending_equity: number;
  net_pnl: number;
  trade_count: number;
  win_count: number;
}

export interface Stats {
  trade_count: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  total_pnl: number;
  entry_signals: number;
  llm_vetoes: number;
  exit_signals: number;
}

export interface WatchlistEntry {
  date: string;
  symbol: string;
  source: string;
  rank: number;
  metrics: Record<string, number>;
  reason: string;
}

export interface Trade {
  id: number;
  ts: string;
  symbol: string;
  side: string;
  qty: number;
  price: number;
  order_id: string;
  pnl: number | null;
  reason: string;
}

export interface Signal {
  id: number;
  ts: string;
  symbol: string;
  signal_type: string;
  details: string;
  llm_action: string | null;
  llm_confidence: number | null;
  llm_reason: string | null;
  rsi: number | null;
  vwap_dev: number | null;
  volume_ratio: number | null;
}

export interface Event {
  id: number;
  ts: string;
  event_type: string;
  message: string;
}

export interface RoundTrip {
  symbol: string;
  buy_ts: string;
  buy_price: number;
  buy_qty: number;
  entry_reason: string | null;
  llm_action: string | null;
  llm_confidence: number | null;
  llm_reason: string | null;
  rsi: number | null;
  vwap_dev: number | null;
  volume_ratio: number | null;
  sell_ts?: string;
  sell_price?: number;
  exit_reason?: string;
  pnl?: number | null;
}

export interface Overview {
  date: string;
  summary: DailySummary | null;
  stats: Stats;
  watchlist: WatchlistEntry[];
  config: Record<string, unknown>;
}

export interface AppConfig {
  symbols: string[];
  strategy: Record<string, number>;
  session: Record<string, string>;
  risk: Record<string, number>;
  execution: Record<string, unknown>;
  briefing: Record<string, unknown>;
  journal_context: Record<string, unknown>;
  screener: Record<string, unknown>;
  llm: Record<string, unknown>;
}
