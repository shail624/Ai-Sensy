import type { ReactNode } from "react";

interface SectionProps {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}

/** A titled card container — the shared shell for every profile section. */
export function Section({ title, action, children }: SectionProps): JSX.Element {
  return (
    <section className="rounded-lg border border-border bg-surface">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        {action}
      </header>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}
