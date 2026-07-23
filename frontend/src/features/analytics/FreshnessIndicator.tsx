import { useAnalyticsFreshness } from "@/features/analytics/api";
import { formatLag } from "@/features/analytics/format";

/**
 * "Data as of …" (Doc 15 §22).
 *
 * A dashboard that cannot say how stale it is will eventually be trusted when it should not be —
 * rollups lag by design (up to the 15-minute incremental cadence), so the lag is stated rather
 * than implied. The stalest kind wins: a summary is only as fresh as its stalest input.
 */
export function FreshnessIndicator(): JSX.Element | null {
  const freshness = useAnalyticsFreshness();
  const rows = freshness.data?.data ?? [];

  if (freshness.isLoading || rows.length === 0) return null;

  const lags = rows.map((row) => row.lag_seconds).filter((lag): lag is number => lag !== null);
  const stalest = lags.length > 0 ? Math.max(...lags) : null;
  const failed = rows.filter((row) => row.last_status === "failed");

  return (
    <p className="text-xs text-text-secondary" role="status">
      Data as of {formatLag(stalest)}
      {failed.length > 0 ? (
        <span className="ml-2 text-danger">
          · {failed.length} rollup{failed.length > 1 ? "s" : ""} failing
        </span>
      ) : null}
    </p>
  );
}
