import { TrendingDown, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  /** Signed fractional change vs a previous period (e.g. 0.12 = +12%). null = unknown. */
  change?: number | null;
  /** When true, a rise is bad (failure/opt-out rates) — colour inverts. */
  invertTrend?: boolean;
  hint?: string;
}

function formatChange(change: number): string {
  return `${change > 0 ? "+" : ""}${(change * 100).toFixed(1)}%`;
}

/** A premium KPI tile: label, big value, coloured trend chip, and an accent icon. */
export function StatCard({ label, value, icon, change, invertTrend = false, hint }: StatCardProps): JSX.Element {
  const hasTrend = change !== null && change !== undefined && change !== 0;
  const positive = (change ?? 0) > 0;
  const good = hasTrend ? positive !== invertTrend : false;
  const Trend = positive ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">{label}</p>
        {icon ? (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            {icon}
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-[26px] font-bold leading-none tracking-tight text-text-primary">{value}</p>
      <div className="mt-3 flex items-center gap-2">
        {hasTrend ? (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-xs font-semibold ${
              good ? "bg-success-soft text-success-on-soft" : "bg-danger-soft text-danger-on-soft"
            }`}
          >
            <Trend aria-hidden className="h-3 w-3" />
            {formatChange(change!)}
          </span>
        ) : null}
        {hint ? <span className="truncate text-xs text-text-disabled">{hint}</span> : null}
      </div>
    </div>
  );
}
