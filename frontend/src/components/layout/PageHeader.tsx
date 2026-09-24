import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Accepted for compatibility; not shown (the reference uses a plain title). */
  eyebrow?: string;
  /** Optional right-aligned actions (buttons, links). */
  actions?: ReactNode;
  /** Compact metadata rendered below the description. */
  meta?: ReactNode;
}

/**
 * The reference page header: a white bar across the top of the page with a plain 20px title,
 * a short grey explanation under it and the page's actions on the right.
 */
export function PageHeader({ title, description, actions, meta }: PageHeaderProps): JSX.Element {
  return (
    <header
      data-slot="page-header"
      className="-mx-4 mb-5 bg-surface px-4 py-4 shadow-card sm:-mx-6 sm:px-6 lg:-mx-[30px] lg:px-[30px]"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-normal leading-7 text-black dark:text-text-primary">{title}</h1>
          {description ? (
            <p className="mt-0.5 max-w-4xl text-[13px] leading-relaxed text-[#6e6e6e] dark:text-text-secondary">{description}</p>
          ) : null}
          {meta ? (
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-text-secondary">{meta}</div>
          ) : null}
        </div>
        {actions ? (
          <div className="flex w-full shrink-0 flex-wrap items-center gap-2 lg:w-auto lg:justify-end">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
