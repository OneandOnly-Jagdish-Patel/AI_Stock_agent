import { TrendingDown, TrendingUp } from "lucide-react";

interface Props {
  label: string;
  value: string;
  change?: string;
  changePct?: string;
  positive?: boolean;
  sub?: string;
}

export function HeroMetric({
  label,
  value,
  change,
  changePct,
  positive,
  sub,
}: Props) {
  const isPositive = positive ?? true;
  const changeClass = isPositive ? "positive" : "negative";
  const Icon = isPositive ? TrendingUp : TrendingDown;

  return (
    <div className="hero-metric">
      <div className="hero-metric-label">{label}</div>
      <div className="hero-metric-value">{value}</div>
      {(change != null || changePct != null) && (
        <div className={`hero-metric-change ${changeClass}`}>
          <Icon size={18} aria-hidden />
          <span>
            {change != null && change}
            {change != null && changePct != null && " "}
            {changePct != null && `(${changePct})`}
          </span>
        </div>
      )}
      {sub && <div className="hero-metric-sub">{sub}</div>}
    </div>
  );
}
