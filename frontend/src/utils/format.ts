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

function fmtPctNum(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function fmtCount(n: number | null | undefined, emptyLabel = "—") {
  if (n == null || (n === 0 && emptyLabel !== "0")) return emptyLabel;
  return String(n);
}

export { fmtTs, fmtMoney, fmtPct, fmtPctNum, fmtCount };
