import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  BulkAction,
  BulkProgress,
  ContactsPage,
  ExportProgress,
  ImportProgress,
  JobAccepted,
  SegmentRule,
} from "@/features/contacts/types";

export interface ContactSearchParams {
  rules: SegmentRule[];
  cursor: string | null;
  limit: number;
}

/**
 * The typed contacts list, via `POST /contacts/search` — the only contacts endpoint whose query is
 * in the OpenAPI contract (`GET /contacts` declares no parameters). Empty `rules` returns everyone,
 * cursor-paginated. `keepPreviousData` keeps the table stable while a new page/filter loads.
 */
export function useContactSearch(params: ContactSearchParams) {
  return useQuery({
    queryKey: ["contacts", "search", params],
    queryFn: async (): Promise<ContactsPage> =>
      unwrap(
        await api.POST("/api/v1/contacts/search", {
          body: {
            match_type: "all",
            rules: params.rules,
            limit: params.limit,
            cursor: params.cursor,
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** How often a running bulk job or export is polled. */
const POLL_MS = 2_000;

/** Job statuses that stop the poll — anything else is still moving (Doc 04 §3). */
const TERMINAL = new Set(["succeeded", "completed", "failed", "cancelled", "partial_success"]);

export interface BulkEditInput {
  ids: string[];
  action: BulkAction;
  /** `{ tags: [...] }` for add/remove, `{ attributes: {...} }` for set (Doc 04 §30). */
  payload: Record<string, unknown>;
}

/**
 * Bulk tag/untag/set-attribute over an explicit selection. Always `202` — the server enqueues the
 * work and this returns the job to poll. `expected_count` is the §30 guard: the server refuses the
 * job when the audience it resolves is not the size the UI thought it was.
 */
export function useBulkEditContacts() {
  return useMutation({
    mutationFn: async ({ ids, action, payload }: BulkEditInput): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/contacts/bulk-update", {
          body: { ids, expected_count: ids.length, action, payload },
        }),
      ),
  });
}

/** Bulk soft-delete over an explicit selection (FR-CON-08). */
export function useBulkDeleteContacts() {
  return useMutation({
    mutationFn: async (ids: string[]): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/contacts/bulk-delete", {
          body: { ids, expected_count: ids.length },
        }),
      ),
  });
}

/**
 * Poll a bulk job until it settles. The response is the §29 partial-success envelope, so the caller
 * gets per-item errors and an error-report link, not just a status.
 */
export function useBulkProgress(bulkId: string | null) {
  return useQuery({
    queryKey: ["contacts", "bulk", bulkId],
    queryFn: async (): Promise<BulkProgress> =>
      unwrap(
        await api.GET("/api/v1/contacts/bulk/{bulk_id}", {
          params: { path: { bulk_id: bulkId! } },
        }),
      ),
    enabled: Boolean(bulkId),
    refetchInterval: (query) => (isSettled(query.state.data) ? false : POLL_MS),
  });
}

/** True once a bulk job has stopped moving. */
export function isSettled(progress: BulkProgress | undefined): boolean {
  return Boolean(progress && TERMINAL.has(progress.job_status));
}

export interface ContactExportInput {
  format: string;
  rules: SegmentRule[];
}

/**
 * Export the current view. The endpoint addresses contacts by rule, not by id, so an export always
 * covers everything the active filters match — the selection cannot narrow it (Doc 04 §30).
 */
export function useStartContactExport() {
  return useMutation({
    mutationFn: async ({ format, rules }: ContactExportInput): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/contacts/export", {
          body: { format, match_type: "all", rules },
        }),
      ),
  });
}

/** Poll an export until its signed link appears, then stop. */
export function useContactExport(exportId: string | null) {
  return useQuery({
    queryKey: ["contacts", "export", exportId],
    queryFn: async (): Promise<ExportProgress> =>
      unwrap(
        await api.GET("/api/v1/contacts/export/{export_id}", {
          params: { path: { export_id: exportId! } },
        }),
      ),
    enabled: Boolean(exportId),
    refetchInterval: (query) =>
      query.state.data?.download_url || query.state.data?.status === "failed" ? false : POLL_MS,
  });
}

export interface ContactImportInput {
  uploadId: string;
  format: string;
  /** `{ csvHeader: target }`, where a target is a contact field or `attr.<key>` (Doc 04 §30). */
  mapping: Record<string, string>;
  dedupStrategy: string;
}

/** Start an import over an already-uploaded file. Always `202` — the rows are read by a worker. */
export function useStartContactImport() {
  return useMutation({
    mutationFn: async ({
      uploadId,
      format,
      mapping,
      dedupStrategy,
    }: ContactImportInput): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/contacts/import", {
          body: { upload_id: uploadId, format, mapping, dedup_strategy: dedupStrategy },
        }),
      ),
  });
}

/** Poll an import until it stops moving. */
export function useContactImport(importId: string | null) {
  return useQuery({
    queryKey: ["contacts", "import", importId],
    queryFn: async (): Promise<ImportProgress> =>
      unwrap(
        await api.GET("/api/v1/contacts/import/{import_id}", {
          params: { path: { import_id: importId! } },
        }),
      ),
    enabled: Boolean(importId),
    refetchInterval: (query) => (TERMINAL.has(query.state.data?.status ?? "") ? false : POLL_MS),
  });
}

/** True once an import has finished, whether or not every row landed. */
export function importIsSettled(progress: ImportProgress | undefined): boolean {
  return Boolean(progress && TERMINAL.has(progress.status));
}

/** Drop every cached contact list — call once a bulk job has changed the underlying rows. */
export function useInvalidateContacts(): () => void {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["contacts", "search"] });
  };
}
