import type { ReactElement } from "react";
import { ResponsiveContainer } from "recharts";

interface Props {
  title: string;
  summary: string;
  children: ReactElement;
  className?: string;
  /** Fixed pixel height — Recharts needs a static value with React 19 */
  height?: number;
}

const DEFAULT_HEIGHT = 280;
const TALL_HEIGHT = 320;

/** Wraps charts with accessible title + screen-reader summary per ui-ux-pro-max chart guidelines */
export function ChartPanel({
  title,
  summary,
  children,
  className = "",
  height = DEFAULT_HEIGHT,
}: Props) {
  return (
    <div
      className={`chart-panel ${className}`.trim()}
      role="img"
      aria-label={`${title}. ${summary}`}
    >
      <p className="sr-only">{summary}</p>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export const chartHeights = {
  default: DEFAULT_HEIGHT,
  tall: TALL_HEIGHT,
} as const;
