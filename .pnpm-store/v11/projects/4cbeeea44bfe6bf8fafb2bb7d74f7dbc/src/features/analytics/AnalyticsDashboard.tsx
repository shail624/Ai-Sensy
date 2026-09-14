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
import { ReportSchedules } from "@/features/analytics/ReportSchedules";
import { ReportSavedViews } from "@/features/analytics/ReportSavedViews";
import { FreshnessIndicator } from "@/features/analytics/FreshnessIndicator";
import { KpiCards } from "@/features/analytics/KpiCards";
import { TeamWorkloadTable } from "@/features/analytics/TeamWorkloadTable";
import { SeriesChart } from "@/features/analytics/SeriesChart";
import { EngagementFunnel } from "@/features/analytics/EngagementFunnel";
import { AiFoundationPanel } from "@/features/ai";
import type {
  AnalyticsFilterState,
  Compare,
  Granularity,
  Preset,
} from "@/features/analytics/types";
import {
  COMPARISONS,
  DEFAULT_SERIES_METRICS,
  GRANULARITIES,
  PRESETS,
} from "@/features/analytics/types";
import { useHasPermission } from "@/lib/auth";

const DEFAULT_FILTERS: AnalyticsFilterState = {
  preset: "last_30d",
  from: "",
  to: "",
  granularity: "day",
  compare: "",
};

export function readAnalyticsFilters(params: URLSearchParams): AnalyticsFilterState {
  const rawPreset = params.get("preset") ?? "";
  const validPreset = PRESETS.some((item) => item.value === rawPreset)
    ? (rawPreset as Preset)
    : "";
  const from = validPreset ? "" : (params.get("from") ?? "");
  const to = validPreset ? "" : (params.get("to") ?? "");
  const rawGranularity = params.get("granularity") ?? "";
  const rawCompare = params.get("compare") ?? "";
  return {
    preset: validPreset || (from || to ? "" : DEFAULT_FILTERS.preset),
    from,
    to,
    granularity: GRANULARITIES.some((item) => item.value === rawGranularity)
      ? (rawGranularity as Granularity)
      : DEFAULT_FILTERS.granularity,
    compare: COMPARISONS.some((item) => item.value === rawCompare)
      ? (rawCompare as Compare)
      : "",
  };
}

export function writeAnalyticsFilters(filters: AnalyticsFilterState): URLSearchParams {
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
 * Historical values read Analytics rollups through the generated client. The separately labelled
 * current-work table reads the Team workload authority because pending stock must never be added
 * across time. Filter state lives in the URL, so a historical view is linkable and refresh-safe.
 */
export function AnalyticsDashboard(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readAnalyticsFilters(searchParams), [searchParams]);
  const isExecutive = useHasPermission("analytics:executive");
  const canViewTeamWorkload = useHasPermission("tasks:assign");

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
  const taskAgents = useAnalyticsBreakdown(filters, "assigned_agent_id", {
    metrics: [
      "tasks_created",
      "tasks_completed",
      "tasks_completed_on_time",
      "tasks_overdue_entered",
    ],
  });
  const costs = useAnalyticsBreakdown(filters, "message_type", {
    metrics: ["cost_micros", "messages_delivered"],
    enabled: isExecutive,
  });
  const reactivationOutcomes = useAnalyticsBreakdown(filters, "outcome", {
    metrics: [
      "reactivation_cases_created",
      "reactivation_completed",
      "reactivation_not_required",
      "eligibility_eligible",
    ],
    limit: 20,
  });
  const kycOutcomes = useAnalyticsBreakdown(filters, "outcome", {
    metrics: ["kyc_decisions", "kyc_approved", "kyc_rejected", "kyc_needs_information"],
    limit: 20,
  });
  const serviceLevels = useAnalyticsBreakdown(filters, "outcome", {
    metrics: [
      "sla_started",
      "sla_breached",
      "sla_resolved",
      "sim_delivered",
      "activations_completed",
    ],
    limit: 20,
  });
  const leadSources = useAnalyticsBreakdown(filters, "source", {
    metrics: ["reactivation_cases_created"],
    limit: 20,
  });

  function apply(next: AnalyticsFilterState): void {
    setSearchParams(writeAnalyticsFilters(next));
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
      <nav aria-label="Analytics dashboards" className="sticky top-0 z-10 flex gap-1 overflow-x-auto rounded-xl border border-border bg-[color-mix(in_srgb,var(--color-bg-surface)_94%,transparent)] p-1.5 shadow-sm backdrop-blur-xl">
        {[
          ["overview", "Overview"], ["delivery", "Delivery & read"], ["campaigns", "Campaigns"],
          ["templates", "Templates"], ["employees", "Employees"],
          ["outcomes", "Business outcomes"], ["exports", "Export center"],
        ].map(([id, label]) => <a key={id} href={`#analytics-${id}`} className="min-h-9 shrink-0 rounded-lg px-3 py-2 text-xs font-semibold text-text-secondary hover:bg-hover hover:text-text-primary">{label}</a>)}
      </nav>

      <div id="analytics-overview" className="scroll-mt-20">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <AnalyticsFilters filters={filters} onChange={apply} />
        <div className="flex flex-col items-end gap-2">
          <FreshnessIndicator />
        </div>
      </div>
      </div>

      <ReportSavedViews filters={filters} onApply={apply} />

      {summary.isLoading ? (
        <Spinner label="Loading analytics…" />
      ) : (
        <KpiCards
          kpis={summary.data?.kpis}
          previous={filters.compare ? comparison.data?.previous_kpis : undefined}
        />
      )}

      <div id="analytics-delivery" className="scroll-mt-20">
      <Section title="Delivery and read trends">
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
      </div>

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

        <div id="analytics-campaigns" className="scroll-mt-20">
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
        </div>

        <div id="analytics-employees" className="scroll-mt-20 xl:col-span-2">
        <Section title="Team productivity" description="Historical throughput from immutable conversation and task events, plus a separate current-work snapshot.">
          <div className="grid gap-4 xl:grid-cols-2">
            <BreakdownTable
              title="Conversation productivity"
              query={agents}
              columns={[
                { key: "conversations_opened", label: "Opened" },
                { key: "conversations_resolved", label: "Resolved" },
                { key: "outbound_messages", label: "Replies" },
              ]}
              rateKey="resolution_rate"
              rateLabel="Resolved"
            />
            <BreakdownTable
              title="Task productivity"
              query={taskAgents}
              columns={[
                { key: "tasks_created", label: "Created" },
                { key: "tasks_completed", label: "Completed" },
                { key: "tasks_completed_on_time", label: "On time" },
                { key: "tasks_overdue_entered", label: "Became overdue" },
              ]}
              rateKey="task_completion_rate"
              rateLabel="Completed"
            />
          </div>
          {canViewTeamWorkload ? (
            <div className="mt-4 border-t border-border pt-4">
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-text-primary">Current workload</h3>
                <p className="mt-1 text-xs text-text-secondary">Live unresolved conversations and open follow-up tasks by teammate.</p>
              </div>
              <TeamWorkloadTable enabled />
            </div>
          ) : null}
        </Section>
        </div>

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

      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Engagement funnel" description="Verified sent, delivered, and read totals for the selected range.">
          <EngagementFunnel totals={summary.data?.totals} />
        </Section>
        <div id="analytics-templates" className="scroll-mt-20">
          <Section title="Template performance">
            <p className="rounded-xl border border-border bg-surface-subtle px-4 py-3 text-sm leading-relaxed text-text-secondary">
              Template approval and quality are available in Template Center. The current analytics contract does not carry a template dimension, so usage performance is not inferred from campaign names.
            </p>
          </Section>
        </div>
      </div>

      <div id="analytics-outcomes" className="scroll-mt-20">
        <Section
          title="Business outcomes"
          description="Reactivation, KYC, fulfilment and SLA facts from the immutable operational event ledger."
        >
          <div className="grid gap-4 xl:grid-cols-2">
            <BreakdownTable
              title="Reactivation outcome"
              query={reactivationOutcomes}
              columns={[
                { key: "reactivation_cases_created", label: "Created" },
                { key: "reactivation_completed", label: "Completed" },
                { key: "reactivation_not_required", label: "Not required" },
                { key: "eligibility_eligible", label: "Eligible" },
              ]}
            />
            <BreakdownTable
              title="KYC outcome"
              query={kycOutcomes}
              columns={[
                { key: "kyc_decisions", label: "Decisions" },
                { key: "kyc_approved", label: "Approved" },
                { key: "kyc_rejected", label: "Rejected" },
                { key: "kyc_needs_information", label: "Needs info" },
              ]}
            />
            <BreakdownTable
              title="Service outcome"
              query={serviceLevels}
              columns={[
                { key: "sla_started", label: "Started" },
                { key: "sla_breached", label: "Breached" },
                { key: "sla_resolved", label: "Resolved" },
                { key: "sim_delivered", label: "SIM delivered" },
                { key: "activations_completed", label: "Activated" },
              ]}
            />
            <BreakdownTable
              title="Lead source"
              query={leadSources}
              columns={[{ key: "reactivation_cases_created", label: "Cases created" }]}
            />
          </div>
        </Section>
      </div>

      <div id="analytics-exports" className="scroll-mt-20">
        <Section title="Export center" description="Create governed CSV, Excel, JSON, or PDF evidence from the active date range.">
          <ExportActions filters={filters} />
        </Section>
        <Section title="Scheduled reports" description="Recurring executive evidence packs, delivered automatically.">
          <ReportSchedules />
        </Section>
      </div>

      <AiFoundationPanel capabilities={["insights"]} context="the verified analytics rollups and selected date range" />
    </div>
  );
}
