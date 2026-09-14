import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  /** A lucide icon element, shown in a soft accent circle above the title. */
  icon?: ReactNode;
  /** Primary call-to-action — an empty screen should always offer the next step. */
  action?: ReactNode;
  /** Compact variant for inside a small panel (no big icon halo, less padding). */
  compact?: boolean;
}

/** "No data" / "nothing yet" state — never a dead end: it names the state and offers a next step. */
export function EmptyState({ title, description, icon, action, compact = false }: EmptyStateProps): JSX.Element {
  return (
    <div className={`flex flex-col items-center text-center ${compact ? "py-6" : "py-12"}`}>
      {icon && !compact ? (
        <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-soft text-accent">
          {icon}
        </span>
      ) : null}
      <p className={`font-semibold text-text-primary ${compact ? "text-sm" : "text-base"}`}>{title}</p>
      {description ? (
        <p className="mt-1.5 max-w-sm text-sm text-text-secondary">{description}</p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
