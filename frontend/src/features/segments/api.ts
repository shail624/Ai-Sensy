import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  Segment,
  SegmentContactsPage,
  SegmentCreateRequest,
  SegmentUpdateRequest,
} from "@/features/segments/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

// The custom-attribute and tag catalogs are owned by the campaigns feature; importing its hooks
// shares one cache rather than growing a second query against the same endpoints.
export { useAttributeDefinitions, useTags } from "@/features/campaigns/api";

export const segmentKeys = {
  all: ["segments"] as const,
  list: () => ["segments", "list"] as const,
  detail: (id: string) => ["segments", "detail", id] as const,
  preview: (id: string) => ["segments", "preview", id] as const,
};

/**
 * Every segment in the organization.
 *
 * `GET /segments` takes **no parameters at all** — not undeclared ones, none — and returns the
 * complete list with its cached counts. Search, filtering and sorting therefore run in the client
 * over a set that is genuinely complete, so nothing is hidden behind a page boundary here.
 */
export function useSegments() {
  return useQuery({
    queryKey: segmentKeys.list(),
    queryFn: async (): Promise<Segment[]> => unwrap(await api.GET("/api/v1/segments")),
  });
}

export function useSegment(segmentId: string, enabled = true) {
  return useQuery({
    queryKey: segmentKeys.detail(segmentId),
    queryFn: async (): Promise<Segment> =>
      unwrap(
        await api.GET("/api/v1/segments/{segment_id}", {
          params: { path: { segment_id: segmentId } },
        }),
      ),
    enabled: enabled && Boolean(segmentId),
  });
}

/**
 * The contacts a segment currently matches.
 *
 * Evaluated live against the compiled rule tree — this is not the cached count, it is the query
 * itself — so it is the authoritative answer to "who is in this segment right now". Cursor-paginated
 * at 50 by contract; `limit` and `cursor` are read off `request.query_params` and are not declared,
 * so this reads the first page and reports the true total alongside it.
 */
export function useSegmentPreview(segmentId: string, enabled = true) {
  return useQuery({
    queryKey: segmentKeys.preview(segmentId),
    queryFn: async (): Promise<SegmentContactsPage> =>
      unwrap(
        await api.GET("/api/v1/segments/{segment_id}/contacts", {
          params: { path: { segment_id: segmentId } },
        }),
      ),
    enabled: enabled && Boolean(segmentId),
    placeholderData: keepPreviousData,
  });
}

/**
 * Every segment write is audited, so the audit trail is invalidated alongside the segment itself.
 * The preview is invalidated too: changing the rules changes who matches.
 */
function useSegmentMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: segmentKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

/** Names are unique within the organization — a duplicate answers 409. */
export function useCreateSegment() {
  return useSegmentMutation(
    async (body: SegmentCreateRequest): Promise<Segment> =>
      unwrap(await api.POST("/api/v1/segments", { body })),
  );
}

/**
 * Update a segment.
 *
 * Rules are **replaced wholesale** when supplied: the request carries the complete set, and the
 * server rebuilds the rule rows from it. Omitting `rules` leaves them alone.
 *
 * Changing rules or the match type **invalidates the cached count** server-side — both
 * `cached_count` and `last_evaluated_at` are reset to null — so a segment reads as un-evaluated
 * until it is refreshed. That is deliberate: a stale number is worse than none.
 */
export function useUpdateSegment() {
  return useSegmentMutation(
    async ({
      segmentId,
      body,
    }: {
      segmentId: string;
      body: SegmentUpdateRequest;
    }): Promise<Segment> =>
      unwrap(
        await api.PATCH("/api/v1/segments/{segment_id}", {
          params: { path: { segment_id: segmentId } },
          body,
        }),
      ),
  );
}

/**
 * Soft-delete a segment.
 *
 * The server applies **no usage guard**: a segment a campaign targets can be deleted, and that
 * campaign's audience would no longer resolve. The confirmation says so rather than the operator
 * discovering it at dispatch.
 */
export function useDeleteSegment() {
  return useSegmentMutation(async (segmentId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/segments/{segment_id}", {
      params: { path: { segment_id: segmentId } },
    });
    if (error !== undefined) throw error;
  });
}

/**
 * Recompute and cache the segment's size.
 *
 * Gated on `segments:read`, not write (Doc 04 §14.3) — recomputing a count is a read of the
 * contact set, so anyone who may see the segment may ask for its current size.
 */
export function useRefreshSegment() {
  return useSegmentMutation(
    async (segmentId: string): Promise<Segment> =>
      unwrap(
        await api.POST("/api/v1/segments/{segment_id}/refresh", {
          params: { path: { segment_id: segmentId } },
        }),
      ),
  );
}
