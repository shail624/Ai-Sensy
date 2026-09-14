import type { components, operations } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 15 §2).
export type AnalyticsSummary = components["schemas"]["AnalyticsSummaryResponse"];
export type AnalyticsKpis = components["schemas"]["AnalyticsKpiResponse"];
export type AnalyticsSeries = components["schemas"]["AnalyticsSeriesResponse"];
export type AnalyticsComparison = components["schemas"]["AnalyticsComparisonResponse"];
export type AnalyticsBreakdown = components["schemas"]["AnalyticsBreakdownResponse"];
export type AnalyticsFreshness = components["schemas"]["AnalyticsFreshnessResponse"];
export type BreakdownRow = components["schemas"]["BreakdownRow"];
export type Series = components["schemas"]["Series"];
export type SeriesPoint = components["schemas"]["SeriesPoint"];
export type ReportExportRequest = components["schemas"]["ReportExportRequest"];
export type ExportProgress = components["schemas"]["ExportProgressResponse"];
export type JobAccepted = components["schemas"]["JobAcceptedResponse"];
export type ReportSchedule = components["schemas"]["ReportScheduleResponse"];
export type ReportScheduleCreate = components["schemas"]["ReportScheduleCreate"];
export type ReportScheduleUpdate = components["schemas"]["ReportScheduleUpdate"];
export type ReportView = components["schemas"]["ReportViewResponse"];
export type ReportViewCreate = components["schemas"]["ReportViewCreate"];
export type TeamWorkload = components["schemas"]["TeamWorkloadResponse"];
export type TeamWorkloadRow = components["schemas"]["TeamWorkloadRow"];

type SeriesQuery = operations["analytics_series_api_v1_analytics_series_get"]["parameters"]["query"];

export type Granularity = NonNullable<SeriesQuery["granularity"]>;
export type Preset = NonNullable<NonNullable<SeriesQuery["preset"]>>;
export type Compare = NonNullable<NonNullable<SeriesQuery["compare"]>>;
export type ReportName = ReportExportRequest["report"];
export type ExportFormat = ReportExportRequest["format"];

/** The range/granularity state every analytics query shares (Doc 15 §14.2). */
export interface AnalyticsFilterState {
  preset: Preset | "";
  from: string;
  to: string;
  granularity: Granularity;
  compare: Compare | "";
}

export const PRESETS: { value: Preset; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "last_7d", label: "Last 7 days" },
  { value: "last_30d", label: "Last 30 days" },
  { value: "this_month", label: "This month" },
  { value: "last_month", label: "Last month" },
  { value: "this_quarter", label: "This quarter" },
];

export const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "hour", label: "Hourly" },
  { value: "day", label: "Daily" },
  { value: "week", label: "Weekly" },
  { value: "month", label: "Monthly" },
];

export const COMPARISONS: { value: Compare; label: string }[] = [
  { value: "previous_period", label: "Previous period" },
  { value: "previous_year", label: "Previous year" },
];

export const REPORTS: { value: ReportName; label: string }[] = [
  { value: "messages", label: "Messages" },
  { value: "failures", label: "Failures" },
  { value: "campaigns", label: "Campaigns" },
  { value: "conversations", label: "Conversations" },
  { value: "tasks", label: "Tasks" },
  { value: "customers", label: "Customers" },
  { value: "costs", label: "Costs" },
  { value: "reactivation", label: "Reactivation outcomes" },
  { value: "kyc", label: "KYC outcomes" },
  { value: "service_levels", label: "Service levels" },
  { value: "team_productivity", label: "Team productivity" },
];

export const EXPORT_FORMATS: ExportFormat[] = ["csv", "xlsx", "json", "pdf"];

export const SCHEDULE_FORMATS = ["pdf", "xlsx", "csv"] as const;
export const SCHEDULE_PRESETS = PRESETS.filter((preset) => preset.value !== "today");
export const SCHEDULE_GRANULARITIES = GRANULARITIES.filter(
  (granularity) => granularity.value !== "hour",
);
export const SCHEDULE_CADENCES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
] as const;
export const WEEKDAYS = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
] as const;

/**
 * KPI cards shown on the dashboard (Doc 15 §11).
 *
 * `kind` decides formatting only — a rate is a fraction, a duration is seconds, `micros` is a
 * money amount in micro-units of the org currency. `null` from the API means *unknown*, never
 * zero: a rate over an empty denominator has no value, and rendering 0% would be a lie.
 */
export type KpiKind = "rate" | "duration" | "micros" | "count";

export interface KpiSpec {
  key: keyof AnalyticsKpis;
  label: string;
  kind: KpiKind;
  /** Executive-only KPIs are hidden without `analytics:executive` (Doc 15 §15). */
  executive?: boolean;
}

export const KPI_CARDS: KpiSpec[] = [
  { key: "delivery_rate", label: "Delivery rate", kind: "rate" },
  { key: "read_rate", label: "Read rate", kind: "rate" },
  { key: "failure_rate", label: "Failure rate", kind: "rate" },
  { key: "avg_delivery_latency_ms", label: "Avg delivery latency", kind: "duration" },
  { key: "resolution_rate", label: "Resolution rate", kind: "rate" },
  { key: "avg_first_response_seconds", label: "Avg first response", kind: "duration" },
  { key: "task_completion_rate", label: "Task completion", kind: "rate" },
  { key: "task_on_time_rate", label: "Tasks on time", kind: "rate" },
  { key: "opt_out_rate", label: "Opt-out rate", kind: "rate" },
  { key: "cost_per_delivered_micros", label: "Cost per delivered", kind: "micros", executive: true },
  { key: "reactivation_conversion_rate", label: "Reactivation conversion", kind: "rate" },
  { key: "kyc_approval_rate", label: "KYC approval", kind: "rate" },
  { key: "sla_breach_rate", label: "SLA breach", kind: "rate" },
  { key: "avg_kyc_turnaround_seconds", label: "Avg KYC turnaround", kind: "duration" },
];

/** The dashboard's default chart metrics — the delivery funnel over time (Doc 15 §11.1). */
export const DEFAULT_SERIES_METRICS = [
  "messages_sent",
  "messages_delivered",
  "messages_read",
  "messages_failed",
];
