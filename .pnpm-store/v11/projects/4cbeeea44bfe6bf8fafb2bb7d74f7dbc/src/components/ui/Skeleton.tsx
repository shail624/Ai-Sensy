interface SkeletonProps {
  className?: string;
}

/** A single shimmering placeholder block. Compose several to mirror the shape of loading content. */
export function Skeleton({ className = "" }: SkeletonProps): JSX.Element {
  return <div aria-hidden className={`animate-pulse rounded-md bg-surface-2 ${className}`} />;
}

/** A ready-made skeleton for a stat/KPI card, so a loading dashboard keeps its layout. */
export function SkeletonStat(): JSX.Element {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-2 h-6 w-20" />
      <Skeleton className="mt-2 h-3 w-16" />
    </div>
  );
}
