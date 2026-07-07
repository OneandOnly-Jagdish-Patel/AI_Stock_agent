export function getChartColors() {
  const s = getComputedStyle(document.documentElement);
  const get = (name: string) => s.getPropertyValue(name).trim();
  return {
    positive: get("--color-positive") || "#00c805",
    negative: get("--color-negative") || "#ff5000",
    accent: get("--color-accent") || "#059669",
    primary: get("--color-primary") || "#334155",
    grid: get("--color-border-subtle") || "#2a2a2e",
    axis: get("--color-text-secondary") || "#8e8e93",
    surface: get("--color-surface") || "#141414",
    border: get("--color-border") || "#333338",
    text: get("--color-text-primary") || "#f5f5f7",
  };
}

export function chartTooltipStyle() {
  const c = getChartColors();
  return {
    background: c.surface,
    border: `1px solid ${c.border}`,
    borderRadius: 8,
    color: c.text,
  };
}
