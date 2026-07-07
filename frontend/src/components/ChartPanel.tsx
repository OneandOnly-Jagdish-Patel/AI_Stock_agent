import type { ReactNode } from "react";

interface Props {
  title: string;
  summary: string;
  children: ReactNode;
  className?: string;
}

/** Wraps charts with accessible title + screen-reader summary per ui-ux-pro-max chart guidelines */
export function ChartPanel({ title, summary, children, className = "" }: Props) {
  return (
    <div
      className={`chart-panel ${className}`.trim()}
      role="img"
      aria-label={`${title}. ${summary}`}
    >
      <p className="sr-only">{summary}</p>
      {children}
    </div>
  );
}
