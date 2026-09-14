import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  AnalyticsBreakdown,
  AnalyticsComparison,
  AnalyticsFilterState,
  AnalyticsFreshness,
  AnalyticsSeries,
  AnalyticsSummary,
  ExportFormat,
  ExportProgress,
  JobAccepted,
  ReportName,
  ReportSchedule,
  ReportScheduleCreate,
  ReportScheduleUpdate,
  ReportView,
  ReportViewCreate,
  TeamWorkload,
} from "@/features/analytics/types";

// Shared error helper, re-exported for this feature's components.
export { apiErrorMessage } from "@/lib/api/errors";

export const analyticsKeys = {
  all: ["analytics"] as const,
  summary: (q: object) => ["analytics", "summary", q] as const,
  series: (q: object) => ["analytics", "series", q] as const,
  comparison: (q: object) => ["analytics", "comparison", q] as const,
  breakdown: (q: object) => ["analytics", "breakdown", q] as const,
  freshness: ["analytics", "freshness"] as const,
  export: (id: string) => ["analytics", "export", id] as const,
  schedules: ["analytics", "report-schedules"] as const,
  views: ["analytics", "views"] as const,
  workload: ["analytics", "team-workload"] as const,
};

export function useReportViews() {
  return useQuery({
    queryKey: analyticsKeys.views,
    queryFn: async (): Promise<ReportView[]> =>
      unwrap(await api.GET("/api/v1/analytics/views")).data,
  });
}

export function useCreateReportView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReportViewCreate): Promise<ReportView> =>
      unwrap(await api.POST("/api/v1/analytics/views", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.views }),
  });
}

export function useDeleteReportView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/analytics/views/{view_id}", {
        params: { path: { view_id: id } },
      });
      if (error !== undefined) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.views }),
  });
}

/**
 * Turn the filter state into the declared query parameters (Doc 15 §14.2).
 *
 * A preset and an explicit range are mutually exclusive — the API requires one or the other, so
 * sending both would be ambiguous. Empty strings become omitted parameters rather than nulls.
 */
export function toRangeQuery(filters: AnalyticsFilterState) {
  const base = { granularity: filters.granularity };
  if (filters.preset) return { ...base, preset: filters.preset };
  return { ...base, from: filters.from || undefined, to: filters.to || undefined };
}

/** Freshness polls on the shared interval so "data as of" never goes quietly stale on screen. */
const FRESHNESS_POLL_MS = 60_000;

export function useAnalyticsSummary(filters: AnalyticsFilterState, metrics?: string[]) {
  const query = { ...toRangeQuery(filters), metrics };
  return useQuery({
    queryKey: analyticsKeys.summary(query),
    queryFn: async (): Promise<AnalyticsSummary> =>
      unwrap(await api.GET("/api/v1/analytics/summary", { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

export function useAnalyticsSeries(filters: AnalyticsFilterState, metrics: string[]) {
  const query = {
    ...toRangeQuery(filters),
    metrics,
    compare: filters.compare || undefined,
  };
  return useQuery({
    queryKey: analyticsKeys.series(query),
    queryFn: async (): Promise<AnalyticsSeries> =>
      unwrap(await api.GET("/api/v1/analytics/series", { params: { query } })),
    placeholderData: keepPreviousData,
    enabled: metrics.length > 0,
  });
}

export function useAnalyticsComparison(filters: AnalyticsFilterState, enabled = true) {
  const query = {
    ...toRangeQuery(filters),
    compare: filters.compare || "previous_period",
  } as const;
  return useQuery({
    queryKey: analyticsKeys.comparison(query),
    queryFn: async (): Promise<AnalyticsComparison> =>
      unwrap(await api.GET("/api/v1/analytics/comparison", { params: { query } })),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useAnalyticsBreakdown(
  filters: AnalyticsFilterState,
  dimension: string,
  options: { metrics?: string[]; limit?: number; enabled?: boolean } = {},
) {
  const query = {
    ...toRangeQuery(filters),
    dimension,
    metrics: options.metrics,
    limit: options.limit ?? 10,
  };
  return useQuery({
    queryKey: analyticsKeys.breakdown(query),
    queryFn: async (): Promise<AnalyticsBreakdown> =>
      unwrap(await api.GET("/api/v1/analytics/breakdown", { params: { query } })),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

/** Rollup watermarks — how stale the dashboard is (Doc 15 §22). */
export function useAnalyticsFreshness() {
  return useQuery({
    queryKey: analyticsKeys.freshness,
    queryFn: async (): Promise<AnalyticsFreshness> =>
      unwrap(await api.GET("/api/v1/analytics/freshness")),
    refetchInterval: FRESHNESS_POLL_MS,
  });
}

/** Start a report export — always 202; the artifact is polled for (Doc 15 §19). */
export function useStartReportExport() {
  return useMutation({
    mutationFn: async ({
      report,
      format,
      filters,
    }: {
      report: ReportName;
      format: ExportFormat;
      filters: AnalyticsFilterState;
    }): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/analytics/reports/export", {
          body: {
            report,
            format,
            filters: {
              granularity: filters.granularity,
              ...(filters.preset
                ? { preset: filters.preset }
                : { from: filters.from || null, to: filters.to || null }),
            },
          },
        }),
      ),
  });
}

/** Poll an export until the artifact is ready, then stop. */
export function useReportExport(exportId: string | null) {
  return useQuery({
    queryKey: analyticsKeys.export(exportId ?? ""),
    queryFn: async (): Promise<ExportProgress> =>
      unwrap(
        await api.GET("/api/v1/analytics/reports/{export_id}", {
          params: { path: { export_id: exportId! } },
        }),
      ),
    enabled: Boolean(exportId),
    refetchInterval: (query) =>
      query.state.data?.download_url || query.state.data?.status === "failed" ? false : 3_000,
  });
}

/** Current stock values live on the Team authority and are never summed as Analytics rollups. */
export function useTeamWorkload(enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.workload,
    queryFn: async (): Promise<TeamWorkload> =>
      unwrap(await api.GET("/api/v1/users/workload")),
    enabled,
  });
}

export function useReportSchedules(enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.schedules,
    queryFn: async (): Promise<ReportSchedule[]> =>
      unwrap(await api.GET("/api/v1/analytics/report-schedules")).data,
    enabled,
  });
}

export function useCreateReportSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReportScheduleCreate): Promise<ReportSchedule> =>
      unwrap(await api.POST("/api/v1/analytics/report-schedules", { body })),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: analyticsKeys.schedules }),
  });
}

export function useUpdateReportSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: ReportScheduleUpdate }) =>
      unwrap(
        await api.PUT("/api/v1/analytics/report-schedules/{schedule_id}", {
          params: { path: { schedule_id: id } },
          body,
        }),
      ),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: analyticsKeys.schedules }),
  });
}

export function useDeleteReportSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, rowVersion }: { id: string; rowVersion: number }) =>
      unwrap(
        await api.DELETE("/api/v1/analytics/report-schedules/{schedule_id}", {
          params: {
            path: { schedule_id: id },
            query: { expected_row_version: rowVersion },
          },
        }),
      ),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: analyticsKeys.schedules }),
  });
}
