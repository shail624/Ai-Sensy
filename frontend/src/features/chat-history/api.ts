import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { InboxFilters } from "@/features/inbox/types";
import type { components } from "@/lib/api/schema";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export type TranscriptFormat = "pdf" | "csv" | "xlsx" | "json";
export type TranscriptExportRequest = components["schemas"]["ConversationTranscriptExportRequest"];
export type ExportProgress = components["schemas"]["ExportProgressResponse"];
export type JobAccepted = components["schemas"]["JobAcceptedResponse"];
export type HistoryView = components["schemas"]["ConversationHistoryViewResponse"];
export type HistoryViewCreate = components["schemas"]["ConversationHistoryViewCreate"];
type SharedFilters = components["schemas"]["ConversationHistoryFilters"];

const transcriptKeys = {
  progress: (id: string) => ["chat-history", "transcript-export", id] as const,
};

export const historyViewKeys = {
  all: ["chat-history", "shared-views"] as const,
};

export function toSharedFilters(filters: InboxFilters): SharedFilters {
  return {
    status: filters.status as SharedFilters["status"],
    assignee: filters.assignee,
    number: filters.number,
    tag: filters.tag,
    q: filters.q,
    from: filters.dateFrom,
    to: filters.dateTo,
    campaign: filters.campaign,
    has_media: Boolean(filters.hasMedia),
    has_audit: Boolean(filters.hasAudit),
  };
}

export function fromSharedFilters(filters: SharedFilters): InboxFilters {
  return {
    status: filters.status ?? undefined,
    assignee: filters.assignee ?? undefined,
    number: filters.number ?? undefined,
    tag: filters.tag ?? undefined,
    q: filters.q ?? undefined,
    dateFrom: filters.from ?? undefined,
    dateTo: filters.to ?? undefined,
    campaign: filters.campaign ?? undefined,
    hasMedia: filters.has_media || undefined,
    hasAudit: filters.has_audit || undefined,
  };
}

export function useHistoryViews() {
  return useQuery({
    queryKey: historyViewKeys.all,
    queryFn: async (): Promise<HistoryView[]> =>
      unwrap(await api.GET("/api/v1/conversation-history/views")).data,
  });
}

export function useCreateHistoryView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: HistoryViewCreate): Promise<HistoryView> =>
      unwrap(await api.POST("/api/v1/conversation-history/views", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: historyViewKeys.all }),
  });
}

export function useDeleteHistoryView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/conversation-history/views/{view_id}", {
        params: { path: { view_id: id } },
      });
      if (error !== undefined) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: historyViewKeys.all }),
  });
}

export function useStartTranscriptExport() {
  return useMutation({
    mutationFn: async (request: TranscriptExportRequest): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/conversation-transcripts/export", {
          body: request,
        }),
      ),
  });
}

/** Poll only while a queued artifact is active; Download Center remains the durable history. */
export function useTranscriptExport(exportId: string | null) {
  return useQuery({
    queryKey: transcriptKeys.progress(exportId ?? ""),
    queryFn: async (): Promise<ExportProgress> =>
      unwrap(
        await api.GET("/api/v1/conversation-transcripts/export/{export_id}", {
          params: { path: { export_id: exportId! } },
        }),
      ),
    enabled: Boolean(exportId),
    refetchInterval: (query) =>
      query.state.data?.download_url || query.state.data?.status === "failed" ? false : 3_000,
  });
}
