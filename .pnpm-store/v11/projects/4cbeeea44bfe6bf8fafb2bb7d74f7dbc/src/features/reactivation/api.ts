import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  EligibilityCheck,
  ReactivationCard,
  ReactivationFilters,
  ReactivationView,
  ReactivationViewCreate,
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
  views: ["reactivation", "views"] as const,
  events: (caseId: string) => ["reactivation", "events", caseId] as const,
  notes: (caseId: string) => ["reactivation", "notes", caseId] as const,
  eligibility: (caseId: string) => ["reactivation", "eligibility", caseId] as const,
};

export function useReactivationViews() {
  return useQuery({
    queryKey: reactivationKeys.views,
    queryFn: async (): Promise<ReactivationView[]> =>
      unwrap(await api.GET("/api/v1/reactivation/views")).data,
  });
}

export function useCreateReactivationView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReactivationViewCreate): Promise<ReactivationView> =>
      unwrap(await api.POST("/api/v1/reactivation/views", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reactivationKeys.views }),
  });
}

export function useDeleteReactivationView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/reactivation/views/{view_id}", {
        params: { path: { view_id: id } },
      });
      if (error !== undefined) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reactivationKeys.views }),
  });
}

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

function useReactivationMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: reactivationKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-profile"] });
    },
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
    }: {
      card: ReactivationCard;
      ownerUserId: string | null;
      previousViNumber: string | null;
      activeDelhiNumber: string | null;
      labels: ReactivationLabel[];
      followUpAt: string | null;
      releaseAt: string | null;
    }) =>
      unwrap(
        await api.PATCH("/api/v1/reactivation-cases/{case_id}", {
          params: { path: { case_id: card.id } },
          body: {
            expected_row_version: card.row_version,
            owner_user_id: ownerUserId,
            previous_vi_number: previousViNumber,
            active_delhi_number: activeDelhiNumber,
            labels,
            follow_up_at: followUpAt,
            release_at: releaseAt,
          },
        }),
      ),
  );
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
