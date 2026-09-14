interface TagChipProps {
  name: string;
  color?: string | null;
  onRemove?: () => void;
  removing?: boolean;
}

/** A tag pill with an optional remove control. Presentational only. */
export function TagChip({ name, color, onRemove, removing }: TagChipProps): JSX.Element {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-2 px-2 py-0.5 text-xs text-text-primary">
      <span
        aria-hidden
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: color ?? "var(--color-text-disabled)" }}
      />
      {name}
      {onRemove ? (
        <button
          type="button"
          aria-label={`Remove tag ${name}`}
          disabled={removing}
          onClick={onRemove}
          className="ml-0.5 rounded-full px-1 text-text-secondary hover:bg-hover disabled:opacity-50"
        >
          ×
        </button>
      ) : null}
    </span>
  );
}
