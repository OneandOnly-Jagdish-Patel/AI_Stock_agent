import type { CSSProperties } from "react";

interface Props {
  className?: string;
  style?: CSSProperties;
}

export function Skeleton({ className = "", style }: Props) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden />;
}

export function OverviewSkeleton() {
  return (
    <div aria-label="Loading dashboard">
      <Skeleton className="skeleton-hero" />
      <div className="metrics-scroll" style={{ marginBottom: "1.5rem" }}>
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="skeleton-card" style={{ width: 160 }} />
        ))}
      </div>
      <Skeleton className="skeleton-chart" />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div aria-label="Loading">
      <Skeleton className="skeleton-hero" style={{ width: "40%", height: 32 }} />
      <Skeleton className="skeleton-chart" style={{ height: 200 }} />
    </div>
  );
}
