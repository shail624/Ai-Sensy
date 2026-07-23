import { Section } from "@/components/ui";
import { delta, formatKpi, formatRate, UNKNOWN } from "@/features/analytics/format";
import type { AnalyticsKpis, KpiSpec } from "@/features/analytics/types";
import { KPI_CARDS } from "@/features/analytics/types";
import { useHasPermission } from "@/lib/auth";

interface CardProps {
  spec: KpiSpec;
  value: number | null | undefined;
  previous?: number | null;
}

function KpiCard({ spec, value, previous }: CardProps): JSX.Element {
  const change = delta(value, previous);
  // For a failure or opt-out rate, "up" is bad — direction alone is not sentiment.
  const inverted = spec.key === "failure_rate" || spec.key === "opt_out_rate";
  const tone =
    change === null || change === 0
      ? "text-text-secondary"
      : (change > 0) !== inverted
        ? "text-success"
        : "text-danger";

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-xs font-medium text-text-secondary">{spec.label}</p>
      <p className="mt-1 text-2xl font-semibold text-text-primary">
        {formatKpi(value, spec.kind)}
      </p>
      {previous !== undefined ? (
        <p className={`mt-1 text-xs ${tone}`}>
          {change === null ? UNKNOWN : `${change > 0 ? "+" : ""}${formatRate(change)}`}
          <span className="text-text-disabled"> vs previous</span>
        </p>
      ) : null}
    </div>
  );
}

interface Props {
  kpis: AnalyticsKpis | undefined;
  previous?: AnalyticsKpis | null;
}

/**
 * The Doc 15 §11 KPI cards. Executive-only KPIs (spend) are hidden without
 * `analytics:executive` — the same permission the API enforces (Doc 15 §15), so the UI never
 * offers a control that would 403.
 */
export function KpiCards({ kpis, previous }: Props): JSX.Element {
  const isExecutive = useHasPermission("analytics:executive");
  const visible = KPI_CARDS.filter((spec) => !spec.executive || isExecutive);

  return (
    <Section title="Key indicators">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {visible.map((spec) => (
          <KpiCard
            key={spec.key}
            spec={spec}
            value={kpis?.[spec.key]}
            previous={previous === undefined ? undefined : (previous?.[spec.key] ?? null)}
          />
        ))}
      </div>
    </Section>
  );
}
