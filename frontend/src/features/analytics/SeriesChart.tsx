import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/ui";
import type { Series } from "@/features/analytics/types";

export type ChartKind = "line" | "area" | "bar";

/**
 * Chart colours come from the design tokens, so light/dark mode is a token swap (Doc 05 DS-3/DS-5)
 * and charts never fight the theme. SVG accepts `var(--…)` directly.
 */
const PALETTE = [
  "var(--color-accent)",
  "var(--color-success)",
  "var(--color-warning)",
  "var(--color-danger)",
  "var(--color-info)",
];

const AXIS_STYLE = { fill: "var(--color-text-secondary)", fontSize: 11 };
const GRID_STROKE = "var(--color-border-default)";

interface Props {
  series: Series[];
  kind?: ChartKind;
  /** Bars only: stack the series instead of grouping them side by side. */
  stacked?: boolean;
  height?: number;
  /** Optional comparison series, rendered dashed behind the primary ones. */
  comparison?: Series[];
}

/** Pivot the API's series-per-metric envelope into the row-per-period shape Recharts wants. */
function toRows(series: Series[], comparison: Series[]): Record<string, string | number>[] {
  const rows = new Map<string, Record<string, string | number>>();
  for (const one of series) {
    for (const point of one.points) {
      const row = rows.get(point.t) ?? { t: point.t };
      row[one.key] = point.v;
      rows.set(point.t, row);
    }
  }
  // The comparison window has its own labels; align it by index so the shapes overlay.
  const labels = [...rows.keys()];
  for (const one of comparison) {
    one.points.forEach((point, index) => {
      const label = labels[index];
      if (label === undefined) return;
      const row = rows.get(label);
      if (row) row[`${one.key}__prev`] = point.v;
    });
  }
  return [...rows.values()];
}

export function SeriesChart({
  series,
  kind = "line",
  stacked = false,
  height = 280,
  comparison = [],
}: Props): JSX.Element {
  if (series.length === 0 || series.every((one) => one.points.length === 0)) {
    return <EmptyState title="No data for this period" />;
  }

  const rows = toRows(series, comparison);
  const axes = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
      <XAxis dataKey="t" tick={AXIS_STYLE} tickLine={false} axisLine={{ stroke: GRID_STROKE }} />
      <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={48} />
      <Tooltip
        contentStyle={{
          background: "var(--color-bg-surface)",
          border: `1px solid ${GRID_STROKE}`,
          borderRadius: 8,
          fontSize: 12,
        }}
      />
      <Legend wrapperStyle={{ fontSize: 12 }} />
    </>
  );

  return (
    // ResponsiveContainer is what makes the chart reflow with the layout rather than at fixed px.
    <ResponsiveContainer width="100%" height={height}>
      {kind === "bar" ? (
        <BarChart data={rows}>
          {axes}
          {series.map((one, index) => (
            <Bar
              key={one.key}
              dataKey={one.key}
              name={one.label}
              stackId={stacked ? "stack" : undefined}
              fill={PALETTE[index % PALETTE.length]}
            />
          ))}
        </BarChart>
      ) : kind === "area" ? (
        <AreaChart data={rows}>
          {axes}
          {series.map((one, index) => (
            <Area
              key={one.key}
              type="monotone"
              dataKey={one.key}
              name={one.label}
              stackId={stacked ? "stack" : undefined}
              stroke={PALETTE[index % PALETTE.length]}
              fill={PALETTE[index % PALETTE.length]}
              fillOpacity={0.18}
            />
          ))}
        </AreaChart>
      ) : (
        <LineChart data={rows}>
          {axes}
          {series.map((one, index) => (
            <Line
              key={one.key}
              type="monotone"
              dataKey={one.key}
              name={one.label}
              stroke={PALETTE[index % PALETTE.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
          {comparison.map((one, index) => (
            <Line
              key={`${one.key}__prev`}
              type="monotone"
              dataKey={`${one.key}__prev`}
              name={`${one.label} (previous)`}
              stroke={PALETTE[index % PALETTE.length]}
              strokeDasharray="4 4"
              strokeOpacity={0.5}
              dot={false}
            />
          ))}
        </LineChart>
      )}
    </ResponsiveContainer>
  );
}
