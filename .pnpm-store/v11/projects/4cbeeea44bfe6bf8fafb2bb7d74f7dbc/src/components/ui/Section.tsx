import type { ReactNode } from "react";

interface SectionProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}

/** A premium titled surface shared by profile, settings, admin and operations panels. */
export function Section({ title, description, icon, action, children }: SectionProps): JSX.Element {
  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3.5">
        <div className="flex min-w-0 items-start gap-3">
          {icon ? (
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
              {icon}
            </span>
          ) : null}
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            {description ? <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">{description}</p> : null}
          </div>
        </div>
        {action}
      </header>
      <div className="px-4 py-4">{children}</div>
    </section>
  );
}
