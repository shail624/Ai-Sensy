import { Check } from "lucide-react";

export interface CampaignWizardStep {
  key: string;
  label: string;
}

interface Props {
  steps: CampaignWizardStep[];
  currentIndex: number;
  includeAnalytics?: boolean;
  onSelect: (index: number) => void;
}

/** Compact, no-scroll progress rail for the governed campaign journey. */
export function CampaignWizardProgress({
  steps,
  currentIndex,
  includeAnalytics = false,
  onSelect,
}: Props): JSX.Element {
  const total = steps.length + (includeAnalytics ? 1 : 0);

  return (
    <nav aria-label="Wizard steps" className="rounded-xl border border-border bg-surface px-2 py-3 sm:px-4">
      <ol
        className="grid items-start"
        style={{ gridTemplateColumns: `repeat(${total}, minmax(0, 1fr))` }}
      >
        {steps.map((step, index) => {
          const completed = index < currentIndex;
          const current = index === currentIndex;

          return (
            <li key={step.key} className="relative min-w-0 text-center">
              {index < total - 1 ? (
                <span
                  aria-hidden
                  className={`absolute left-[calc(50%+1rem)] right-[calc(-50%+1rem)] top-4 h-0.5 ${
                    completed ? "bg-accent" : "bg-border"
                  }`}
                />
              ) : null}
              <button
                type="button"
                disabled={index > currentIndex}
                onClick={() => onSelect(index)}
                aria-current={current ? "step" : undefined}
                className="group relative z-10 inline-flex w-full min-w-0 flex-col items-center gap-1.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-default"
              >
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-bold transition-colors ${
                    completed
                      ? "border-accent bg-accent text-accent-fg"
                      : current
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-border bg-surface text-text-disabled"
                  }`}
                >
                  {completed ? <Check aria-hidden className="h-4 w-4" /> : index + 1}
                </span>
                <span
                  className={`hidden max-w-full px-0.5 text-[11px] font-semibold leading-tight sm:block lg:text-xs ${
                    current ? "text-accent" : completed ? "text-text-primary" : "text-text-disabled"
                  }`}
                >
                  {step.label}
                </span>
              </button>
            </li>
          );
        })}

        {includeAnalytics ? (
          <li className="relative min-w-0 text-center" aria-label="Analytics becomes available after launch">
            <span aria-hidden className="flex flex-col items-center gap-1.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-xs font-bold text-text-disabled">
                {total}
              </span>
              <span className="hidden max-w-full px-0.5 text-[11px] font-semibold leading-tight text-text-disabled sm:block lg:text-xs">
                Analytics
              </span>
            </span>
          </li>
        ) : null}
      </ol>
    </nav>
  );
}
