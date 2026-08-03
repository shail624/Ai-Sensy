import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  /** Lift treatment for cards that are themselves links/actions. */
  interactive?: boolean;
  padding?: boolean;
}

/** The standard enterprise surface: restrained radius, clear border, and low elevation. */
export function Card({
  children,
  className = "",
  interactive = false,
  padding = true,
}: CardProps): JSX.Element {
  return (
    <div
      data-slot="card"
      className={`rounded-xl border border-border bg-surface shadow-sm ${
        padding ? "p-4 sm:p-5" : ""
      } ${
        interactive
          ? "transition-[border-color,box-shadow,background-color] hover:border-[color-mix(in_srgb,var(--color-accent)_38%,var(--color-border-default))] hover:bg-[color-mix(in_srgb,var(--color-bg-surface)_96%,var(--color-accent-soft))] hover:shadow-md"
          : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** A consistent panel header — title, optional description, and a right-aligned action slot. */
export function CardHeader({
  title,
  description,
  icon,
  action,
  className = "",
}: CardHeaderProps): JSX.Element {
  return (
    <div className={`flex items-start justify-between gap-3 ${className}`}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-on-soft">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold leading-5 text-text-primary">{title}</h3>
          {description ? (
            <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">{description}</p>
          ) : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
