import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage } from "@/features/analytics/api";
import { formatCount, formatMicros, formatRate } from "@/features/analytics/format";
import type { AnalyticsBreakdown } from "@/features/analytics/types";

interface Props {
  title: string;
  query: {
    data: AnalyticsBreakdown | undefined;
    isLoading: boolean;
    isError: boolean;
    error: unknown;
    refetch: () => void;
  };
  /** Metric keys to render as columns, in order. */
  columns: { key: string; label: string }[];
  /** Optional derived KPI column (e.g. delivery rate) rendered after the measures. */
  rateKey?: keyof AnalyticsBreakdown["data"][number]["kpis"];
  rateLabel?: string;
}

function cell(key: string, value: number | undefined): string {
  if (value === undefined) return "—";
  return key.endsWith("_micros") ? formatMicros(value) : formatCount(value);
}

/** A ranked grouped table — the Doc 15 §16 family-3 surface, reusing the app's table styling. */
export function BreakdownTable({ title, query, columns, rateKey, rateLabel }: Props): JSX.Element {
  if (query.isLoading) return <Spinner label={`Loading ${title.toLowerCase()}…`} />;
  if (query.isError) {
    return <ErrorState message={apiErrorMessage(query.error)} onRetry={() => query.refetch()} />;
  }

  const rows = query.data?.data ?? [];
  if (rows.length === 0) return <EmptyState title="No data for this period" />;

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="px-3 py-2">{title}</th>
            {columns.map((column) => (
              <th key={column.key} scope="col" className="px-3 py-2 text-right">
                {column.label}
              </th>
            ))}
            {rateKey ? (
              <th scope="col" className="px-3 py-2 text-right">{rateLabel ?? "Rate"}</th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key || row.label} className="border-b border-border last:border-0">
              <td className="px-3 py-2 text-text-primary">{row.label}</td>
              {columns.map((column) => (
                <td key={column.key} className="px-3 py-2 text-right text-text-secondary">
                  {cell(column.key, row.totals[column.key])}
                </td>
              ))}
              {rateKey ? (
                <td className="px-3 py-2 text-right text-text-secondary">
                  {formatRate(row.kpis[rateKey])}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
