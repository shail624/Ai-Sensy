interface EmptyStateProps {
  title: string;
  description?: string;
}

/** Neutral placeholder for "no data" (and "not available") states. */
export function EmptyState({ title, description }: EmptyStateProps): JSX.Element {
  return (
    <div className="py-6 text-center">
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      {description ? <p className="mt-1 text-xs text-text-disabled">{description}</p> : null}
    </div>
  );
}
