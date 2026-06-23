function fmtTs(ts: string) {
  return ts.replace("T", " ").slice(0, 19);
}

function fmtMoney(n: number | null | undefined) {
  if (n == null) return "—";
  const sign = n >= 0 ? "" : "-";
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

function fmtPct(n: number | null | undefined) {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

export { fmtTs, fmtMoney, fmtPct };
