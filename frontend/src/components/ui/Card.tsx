import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  /** Lift on hover — for cards that are themselves links/actions. */
  interactive?: boolean;
  padding?: boolean;
}

/** The surface every panel sits on: rounded, bordered, softly elevated (Doc 05 DS). */
export function Card({ children, className = "", interactive = false, padding = true }: CardProps): JSX.Element {
  return (
    <div
      className={`rounded-2xl border border-border bg-surface shadow-sm ${
        padding ? "p-5" : ""
      } ${interactive ? "transition-all hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] hover:shadow-md" : ""} ${className}`}
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
export function CardHeader({ title, description, icon, action, className = "" }: CardHeaderProps): JSX.Element {
  return (
    <div className={`flex items-start justify-between gap-3 ${className}`}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-text-primary">{title}</h3>
          {description ? <p className="mt-0.5 text-xs text-text-secondary">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
