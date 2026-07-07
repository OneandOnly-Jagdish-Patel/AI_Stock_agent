interface Props {
  label: string;
  value: string | number;
  sub?: string;
  className?: string;
  variant?: "default" | "compact";
}

export function StatCard({
  label,
  value,
  sub,
  className = "",
  variant = "default",
}: Props) {
  return (
    <div
      className={`stat-card${variant === "compact" ? " stat-card--compact" : ""} ${className}`}
    >
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
