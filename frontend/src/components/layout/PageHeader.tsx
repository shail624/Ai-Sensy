import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Small context label above the title, useful for a product area or lifecycle state. */
  eyebrow?: string;
  /** Optional right-aligned actions (buttons, links). */
  actions?: ReactNode;
  /** Compact metadata rendered below the description. */
  meta?: ReactNode;
}

/** Standard page title block. */
export function PageHeader({ title, description, eyebrow, actions, meta }: PageHeaderProps): JSX.Element {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.16em] text-accent">{eyebrow}</p> : null}
        <h1 className="text-2xl font-bold tracking-[-0.025em] text-text-primary sm:text-[28px] sm:leading-9">{title}</h1>
        {description ? <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-text-secondary">{description}</p> : null}
        {meta ? <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-secondary">{meta}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
