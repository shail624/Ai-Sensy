import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useAnalyticsBreakdown,
  useAnalyticsComparison,
  useAnalyticsSeries,
  useAnalyticsSummary,
} from "@/features/analytics/api";
import { AnalyticsFilters } from "@/features/analytics/AnalyticsFilters";
import { BreakdownTable } from "@/features/analytics/BreakdownTable";
import { ExportActions } from "@/features/analytics/ExportActions";
import { FreshnessIndicator } from "@/features/analytics/FreshnessIndicator";
import { KpiCards } from "@/features/analytics/KpiCards";
import { SeriesChart } from "@/features/analytics/SeriesChart";
import type {
  AnalyticsFilterState,
  Compare,
  Granularity,
  Preset,
} from "@/features/analytics/types";
import { DEFAULT_SERIES_METRICS } from "@/features/analytics/types";
import { useHasPermission } from "@/lib/auth";

const DEFAULT_FILTERS: AnalyticsFilterState = {
  preset: "last_30d",
  from: "",
  to: "",
  granularity: "day",
  compare: "",
};

function readFilters(params: URLSearchParams): AnalyticsFilterState {
  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";
  const preset = (params.get("preset") ?? (from || to ? "" : DEFAULT_FILTERS.preset)) as Preset | "";
  return {
    preset,
    from,
    to,
    granularity: (params.get("granularity") as Granularity) ?? DEFAULT_FILTERS.granularity,
    compare: (params.get("compare") ?? "") as Compare | "",
  };
}

function writeFilters(filters: AnalyticsFilterState): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.preset) params.set("preset", filters.preset);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  params.set("granularity", filters.granularity);
  if (filters.compare) params.set("compare", filters.compare);
  return params;
}

/** A loading skeleton that holds the layout, so the page does not jump when data lands. */
function ChartSkeleton(): JSX.Element {
  return (
    <div className="space-y-2" aria-hidden>
      <div className="h-[280px] animate-pulse rounded-md bg-surface-2" />
    </div>
  );
}

/**
 * The Analytics dashboard (Doc 15 §12, §16).
 *
 * Reads **only** analytics endpoints — every number on this page comes from the rollups through
 * the generated client. Filter state lives in the URL, so a view is linkable and a refresh keeps
 * its place, matching the Contacts, Tasks and Inbox modules.
 */
export function AnalyticsDashboard(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const isExecutive = useHasPermission("analytics:executive");

  const summary = useAnalyticsSummary(filters);
  const series = useAnalyticsSeries(filters, DEFAULT_SERIES_METRICS);
  const comparison = useAnalyticsComparison(filters);
  const failures = useAnalyticsBreakdown(filters, "error_code", { metrics: ["failures"] });
  const campaigns = useAnalyticsBreakdown(filters, "campaign_id", {
    metrics: ["campaign_sent", "campaign_delivered", "campaign_read", "campaign_failed"],
  });
  const agents = useAnalyticsBreakdown(filters, "assigned_user_id", {
    metrics: ["conversations_opened", "conversations_resolved", "outbound_messages"],
  });
  const costs = useAnalyticsBreakdown(filters, "message_type", {
    metrics: ["cost_micros", "messages_delivered"],
    enabled: isExecutive,
  });

  function apply(next: AnalyticsFilterState): void {
    setSearchParams(writeFilters(next));
  }

  // The whole page shares one range, so a range failure is a page-level failure.
  if (summary.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(summary.error)}
        onRetry={() => void summary.refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <AnalyticsFilters filters={filters} onChange={apply} />
        <div className="flex flex-col items-end gap-2">
          <FreshnessIndicator />
          <ExportActions filters={filters} />
        </div>
      </div>

      {summary.isLoading ? (
        <Spinner label="Loading analytics…" />
      ) : (
        <KpiCards
          kpis={summary.data?.kpis}
          previous={filters.compare ? comparison.data?.previous_kpis : undefined}
        />
      )}

      <Section title="Delivery over time">
        {series.isLoading ? (
          <ChartSkeleton />
        ) : series.isError ? (
          <ErrorState
            message={apiErrorMessage(series.error)}
            onRetry={() => void series.refetch()}
          />
        ) : (
          <SeriesChart
            series={series.data?.series ?? []}
            comparison={series.data?.comparison ?? []}
            kind="line"
          />
        )}
      </Section>

      <Section title="Volume by period">
        {series.isLoading ? (
          <ChartSkeleton />
        ) : (
          <SeriesChart series={series.data?.series ?? []} kind="bar" stacked height={240} />
        )}
      </Section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Section title="Top failure causes">
          <BreakdownTable
            title="Error code"
            query={failures}
            columns={[{ key: "failures", label: "Failures" }]}
          />
        </Section>

        <Section title="Campaign performance">
          <BreakdownTable
            title="Campaign"
            query={campaigns}
            columns={[
              { key: "campaign_sent", label: "Sent" },
              { key: "campaign_delivered", label: "Delivered" },
              { key: "campaign_read", label: "Read" },
            ]}
            rateKey="campaign_delivery_rate"
            rateLabel="Delivery"
          />
        </Section>

        <Section title="Agent performance">
          <BreakdownTable
            title="Agent"
            query={agents}
            columns={[
              { key: "conversations_opened", label: "Opened" },
              { key: "conversations_resolved", label: "Resolved" },
              { key: "outbound_messages", label: "Replies" },
            ]}
            rateKey="resolution_rate"
            rateLabel="Resolved"
          />
        </Section>

        {isExecutive ? (
          <Section title="Spend by message type">
            <BreakdownTable
              title="Message type"
              query={costs}
              columns={[
                { key: "cost_micros", label: "Spend" },
                { key: "messages_delivered", label: "Delivered" },
              ]}
            />
          </Section>
        ) : null}
      </div>
    </div>
  );
}
