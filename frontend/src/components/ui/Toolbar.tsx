import type { HTMLAttributes, ReactNode } from "react";

interface ToolbarProps extends HTMLAttributes<HTMLDivElement> {
  label?: string;
  density?: "compact" | "comfortable";
  surface?: boolean;
}

/** Flexible action row for dense enterprise pages without imposing ARIA toolbar arrow-key semantics. */
export function Toolbar({
  label,
  density = "compact",
  surface = false,
  className = "",
  children,
  ...props
}: ToolbarProps): JSX.Element {
  return (
    <div
      {...props}
      aria-label={label}
      className={`flex min-w-0 flex-wrap items-center ${
        density === "compact" ? "gap-2" : "gap-3"
      } ${surface ? "rounded-xl border border-border bg-surface p-2.5 shadow-sm" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

interface ToolbarGroupProps extends HTMLAttributes<HTMLDivElement> {
  grow?: boolean;
}

export function ToolbarGroup({
  grow = false,
  className = "",
  children,
  ...props
}: ToolbarGroupProps): JSX.Element {
  return (
    <div
      {...props}
      className={`flex min-w-0 flex-wrap items-center gap-2 ${grow ? "flex-1" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export function ToolbarDivider({ className = "" }: { className?: string }): JSX.Element {
  return <span aria-hidden className={`hidden h-6 w-px bg-border sm:block ${className}`} />;
}

interface FilterBarProps {
  children: ReactNode;
  label?: string;
  className?: string;
  contentClassName?: string;
}

/** Consistent surface for search, filters, saved views, and adjacent list controls. */
export function FilterBar({
  children,
  label = "Filters",
  className = "",
  contentClassName = "",
}: FilterBarProps): JSX.Element {
  return (
    <section
      aria-label={label}
      className={`rounded-xl border border-border bg-surface p-2.5 shadow-sm ${className}`}
    >
      <div className={`flex min-w-0 flex-wrap items-center gap-2 ${contentClassName}`}>
        {children}
      </div>
    </section>
  );
}
