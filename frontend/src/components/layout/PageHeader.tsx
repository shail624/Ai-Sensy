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

/** Standard enterprise page title block with stable action and metadata alignment. */
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  meta,
}: PageHeaderProps): JSX.Element {
  return (
    <header data-slot="page-header" className="mb-5 border-b border-border pb-5 sm:mb-6 sm:pb-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          {eyebrow ? (
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.16em] text-accent-on-soft">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="text-[26px] font-bold leading-8 tracking-[-0.025em] text-text-primary sm:text-[30px] sm:leading-9">
            {title}
          </h1>
          {description ? (
            <p className="mt-1.5 max-w-4xl text-sm leading-relaxed text-text-secondary">
              {description}
            </p>
          ) : null}
          {meta ? (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-text-secondary">
              {meta}
            </div>
          ) : null}
        </div>
        {actions ? (
          <div className="flex w-full shrink-0 flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
            {actions}
          </div>
        ) : null}
      </div>
    </header>
  );
}
