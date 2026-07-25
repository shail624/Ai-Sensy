import { EmptyState } from "@/components/ui";
import { formatCount } from "@/lib/format";

interface Props {
  totals: Record<string, number> | undefined;
}

/** A factual delivery funnel derived only from the analytics summary totals. */
export function EngagementFunnel({ totals }: Props): JSX.Element {
  const steps = [
    { key: "messages_sent", label: "Sent" },
    { key: "messages_delivered", label: "Delivered" },
    { key: "messages_read", label: "Read" },
  ].map((step) => ({ ...step, value: totals?.[step.key] ?? 0 }));
  const maximum = Math.max(...steps.map((step) => step.value), 0);

  if (maximum === 0) {
    return <EmptyState compact title="No delivery funnel yet" description="The funnel appears when verified message rollups exist for this range." />;
  }

  return (
    <ol className="space-y-3" aria-label="Message delivery funnel">
      {steps.map((step, index) => {
        const width = Math.max(12, Math.round((step.value / maximum) * 100));
        const previous = index > 0 ? steps[index - 1]!.value : null;
        const rate = previous && previous > 0 ? step.value / previous : null;
        return (
          <li key={step.key}>
            <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
              <span className="font-semibold text-text-primary">{step.label}</span>
              <span className="text-text-secondary">{formatCount(step.value)}{rate !== null ? ` · ${(rate * 100).toFixed(1)}%` : ""}</span>
            </div>
            <div className="h-9 overflow-hidden rounded-xl bg-surface-2">
              <div className="flex h-full items-center rounded-xl bg-accent px-3 text-xs font-semibold text-accent-fg transition-[width] duration-500 motion-reduce:transition-none" style={{ width: `${width}%` }}>
                {step.label}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
