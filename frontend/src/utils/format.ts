/** Display timezone for all dashboard timestamps and labels. */
export const DISPLAY_TZ = "America/Chicago";
export const DISPLAY_TZ_LABEL = "CST";

function fmtTs(ts: string) {
  if (!ts) return "—";
  const normalized =
    ts.includes("Z") || ts.includes("+") || ts.includes("-", 10)
      ? ts
      : `${ts}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) {
    return ts.replace("T", " ").slice(0, 19);
  }
  return new Intl.DateTimeFormat("en-US", {
    timeZone: DISPLAY_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
    .format(d)
    .replace(",", "");
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
