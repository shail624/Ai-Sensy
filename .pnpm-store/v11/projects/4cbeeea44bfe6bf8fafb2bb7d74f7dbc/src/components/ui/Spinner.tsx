interface SpinnerProps {
  label?: string;
  className?: string;
}

/** Accessible inline loading indicator. */
export function Spinner({ label = "Loading…", className }: SpinnerProps): JSX.Element {
  return (
    <span
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-2 text-sm text-text-secondary ${className ?? ""}`}
    >
      <span
        aria-hidden
        className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent"
      />
      {label}
    </span>
  );
}
