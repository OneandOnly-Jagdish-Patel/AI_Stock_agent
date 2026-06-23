interface Props {
  label: string;
  value: string | number;
  sub?: string;
  className?: string;
}

export function StatCard({ label, value, sub, className = "" }: Props) {
  return (
    <div className={`stat-card ${className}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
