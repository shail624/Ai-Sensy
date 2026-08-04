import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  EligibilityCheck,
  ReactivationCard,
  ReactivationFilters,
  ReactivationNote,
  ReactivationLabel,
  ReactivationPipeline,
  ReactivationStage,
  ReactivationStageEvent,
} from "@/features/reactivation/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export const reactivationKeys = {
  all: ["reactivation"] as const,
  pipeline: (filters: ReactivationFilters) => ["reactivation", "pipeline", filters] as const,
  events: (caseId: string) => ["reactivation", "events", caseId] as const,
  notes: (caseId: string) => ["reactivation", "notes", caseId] as const,
  eligibility: (caseId: string) => ["reactivation", "eligibility", caseId] as const,
};

export function useReactivationPipeline(filters: ReactivationFilters, enabled = true) {
  return useQuery({
    queryKey: reactivationKeys.pipeline(filters),
    queryFn: async (): Promise<ReactivationPipeline> =>
      unwrap(
        await api.GET("/api/v1/reactivation-pipeline", {
          params: { query: { ...filters, limit: filters.limit ?? 200 } },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
  });
}

function invalidateReactivationQueries(queryClient: ReturnType<typeof useQueryClient>): void {
  void queryClient.invalidateQueries({ queryKey: reactivationKeys.all });
  void queryClient.invalidateQueries({ queryKey: ["tasks"] });
  void queryClient.invalidateQueries({ queryKey: ["customer-profile"] });
}

function useReactivationMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => invalidateReactivationQueries(queryClient),
  });
}

export function useTransitionReactivation() {
  return useReactivationMutation(
    async ({
      card,
      toStage,
      reason,
    }: {
      card: ReactivationCard;
      toStage: ReactivationStage;
      reason?: string;
    }) =>
      unwrap(
        await api.POST("/api/v1/reactivation-cases/{case_id}/transition", {
          params: { path: { case_id: card.id } },
          body: {
            idempotency_key: crypto.randomUUID(),
            expected_row_version: card.row_version,
            to_stage: toStage,
            reason: reason?.trim() || null,
          },
        }),
      ),
  );
}

interface ReactivationUpdateValues {
  ownerUserId: string | null;
  previousViNumber: string | null;
  activeDelhiNumber: string | null;
  labels: ReactivationLabel[];
  followUpAt: string | null;
  releaseAt: string | null;
}

async function updateReactivationCard(
  card: ReactivationCard,
  values: ReactivationUpdateValues,
) {
  return unwrap(
    await api.PATCH("/api/v1/reactivation-cases/{case_id}", {
      params: { path: { case_id: card.id } },
      body: {
        expected_row_version: card.row_version,
        owner_user_id: values.ownerUserId,
        previous_vi_number: values.previousViNumber,
        active_delhi_number: values.activeDelhiNumber,
        labels: values.labels,
        follow_up_at: values.followUpAt,
        release_at: values.releaseAt,
      },
    }),
  );
}

export function useUpdateReactivation() {
  return useReactivationMutation(
    async ({
      card,
      ownerUserId,
      previousViNumber,
      activeDelhiNumber,
      labels,
      followUpAt,
      releaseAt,
    }: { card: ReactivationCard } & ReactivationUpdateValues) =>
      updateReactivationCard(card, {
        ownerUserId,
        previousViNumber,
        activeDelhiNumber,
        labels,
        followUpAt,
        releaseAt,
      }),
  );
}

export interface ReactivationBulkUpdateRequest {
  cards: ReactivationCard[];
  ownerUserId?: string | null;
  addLabel?: ReactivationLabel;
  removeLabel?: ReactivationLabel;
}

export interface ReactivationBulkUpdateResult {
  updated: number;
  failed: number;
  failedCaseIds: string[];
}

/**
 * Applies one authorized PATCH per selected case. The backend remains the only authority for
 * object-level authorization, tenant isolation, row-version concurrency and audit evidence.
 */
export function useBulkUpdateReactivation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      cards,
      ownerUserId,
      addLabel,
      removeLabel,
    }: ReactivationBulkUpdateRequest): Promise<ReactivationBulkUpdateResult> => {
      const results = await Promise.allSettled(
        cards.map((card) => {
          const labels = card.labels
            .filter((label) => label !== removeLabel)
            .concat(addLabel && !card.labels.includes(addLabel) ? [addLabel] : []);
          return updateReactivationCard(card, {
            ownerUserId: ownerUserId === undefined ? card.owner_user_id : ownerUserId,
            previousViNumber: card.previous_vi_number,
            activeDelhiNumber: card.active_delhi_number,
            labels,
            followUpAt: card.follow_up_at,
            releaseAt: card.release_at,
          });
        }),
      );
      const failedCaseIds = results.flatMap((result, index) =>
        result.status === "rejected" ? [cards[index]?.id ?? "unknown"] : [],
      );
      return {
        updated: results.length - failedCaseIds.length,
        failed: failedCaseIds.length,
        failedCaseIds,
      };
    },
    onSettled: () => invalidateReactivationQueries(queryClient),
  });
}

export function useReactivationEvents(caseId: string) {
  return useQuery({
    queryKey: reactivationKeys.events(caseId),
    queryFn: async (): Promise<ReactivationStageEvent[]> =>
      unwrap(
        await api.GET("/api/v1/reactivation-cases/{case_id}/stage-events", {
          params: { path: { case_id: caseId } },
        }),
      ).data,
    enabled: Boolean(caseId),
  });
}

export function useReactivationNotes(caseId: string) {
  return useQuery({
    queryKey: reactivationKeys.notes(caseId),
    queryFn: async (): Promise<ReactivationNote[]> =>
      unwrap(
        await api.GET("/api/v1/reactivation-cases/{case_id}/notes", {
          params: { path: { case_id: caseId } },
        }),
      ).data,
    enabled: Boolean(caseId),
  });
}

export function useAddReactivationNote(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: string): Promise<ReactivationNote> =>
      unwrap(
        await api.POST("/api/v1/reactivation-cases/{case_id}/notes", {
          params: { path: { case_id: caseId } },
          body: { body },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: reactivationKeys.notes(caseId) });
      void queryClient.invalidateQueries({ queryKey: ["customer-profile"] });
    },
  });
}

export function useEligibilityChecks(caseId: string) {
  return useQuery({
    queryKey: reactivationKeys.eligibility(caseId),
    queryFn: async (): Promise<EligibilityCheck[]> =>
      unwrap(
        await api.GET("/api/v1/reactivation-cases/{case_id}/eligibility-checks", {
          params: { path: { case_id: caseId } },
        }),
      ).data,
    enabled: Boolean(caseId),
  });
}

export function useRecordEligibility(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      status,
      reason,
    }: {
      status: "eligible" | "not_eligible" | "review_required";
      reason?: string;
    }): Promise<EligibilityCheck> =>
      unwrap(
        await api.POST("/api/v1/reactivation-cases/{case_id}/eligibility-checks", {
          params: { path: { case_id: caseId } },
          body: {
            idempotency_key: crypto.randomUUID(),
            status,
            source: "manual",
            reason: reason?.trim() || null,
            approval_reference: null,
          },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: reactivationKeys.all });
    },
  });
}
