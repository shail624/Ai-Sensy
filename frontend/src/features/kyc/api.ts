import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  KycAppointment,
  KycCase,
  KycDecision,
  KycDocumentPurpose,
  KycDocumentReference,
  KycFilters,
  KycOperationsResponse,
  KycReasonCode,
  KycStatus,
} from "@/features/kyc/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export const kycKeys = {
  all: ["kyc"] as const,
  operations: (filters: KycFilters) => ["kyc", "operations", filters] as const,
  contact: (contactId: string) => ["kyc", "contact", contactId] as const,
  decisions: (kycId: string) => ["kyc", "decisions", kycId] as const,
};

export function useKycOperations(filters: KycFilters, enabled = true) {
  return useQuery({
    queryKey: kycKeys.operations(filters),
    queryFn: async (): Promise<KycOperationsResponse> =>
      unwrap(
        await api.GET("/api/v1/kyc-operations", {
          params: { query: { ...filters, limit: filters.limit ?? 200 } },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useContactKycCases(contactId: string, enabled = true) {
  return useQuery({
    queryKey: kycKeys.contact(contactId),
    queryFn: async (): Promise<KycCase[]> =>
      unwrap(
        await api.GET("/api/v1/contacts/{contact_id}/kyc-cases", {
          params: { path: { contact_id: contactId } },
        }),
      ).data,
    enabled: enabled && Boolean(contactId),
  });
}

export function useKycDecisions(kycId: string) {
  return useQuery({
    queryKey: kycKeys.decisions(kycId),
    queryFn: async (): Promise<KycDecision[]> =>
      unwrap(
        await api.GET("/api/v1/kyc-cases/{kyc_id}/decisions", {
          params: { path: { kyc_id: kycId } },
        }),
      ).data,
    enabled: Boolean(kycId),
  });
}

function useKycMutation<TVariables, TData>(mutationFn: (variables: TVariables) => Promise<TData>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: kycKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["reactivation"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-profile"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useCreateKycCase() {
  return useKycMutation(
    async ({ caseId, ownerUserId }: { caseId: string; ownerUserId?: string | null }): Promise<KycCase> =>
      unwrap(
        await api.POST("/api/v1/reactivation-cases/{case_id}/kyc-cases", {
          params: { path: { case_id: caseId } },
          body: {
            idempotency_key: crypto.randomUUID(),
            owner_user_id: ownerUserId ?? null,
            appointment_at: null,
          },
        }),
      ),
  );
}

export function useUpdateKycCase() {
  return useKycMutation(
    async ({
      kycId,
      expectedRowVersion,
      status,
      ownerUserId,
      holderVerified,
      delhiPresenceVerified,
      activeDelhiNumberVerified,
    }: {
      kycId: string;
      expectedRowVersion: number;
      status: Exclude<KycStatus, "approved" | "rejected">;
      ownerUserId: string | null;
      holderVerified: boolean;
      delhiPresenceVerified: boolean;
      activeDelhiNumberVerified: boolean;
    }): Promise<KycCase> =>
      unwrap(
        await api.PATCH("/api/v1/kyc-cases/{kyc_id}", {
          params: { path: { kyc_id: kycId } },
          body: {
            expected_row_version: expectedRowVersion,
            status,
            owner_user_id: ownerUserId,
            holder_verified: holderVerified,
            delhi_presence_verified: delhiPresenceVerified,
            active_delhi_number_verified: activeDelhiNumberVerified,
            appointment_at: null,
          },
        }),
      ),
  );
}

export function useSetKycDocumentReference() {
  return useKycMutation(
    async ({
      kycId,
      purpose,
      documentId,
      expectedRowVersion,
    }: {
      kycId: string;
      purpose: KycDocumentPurpose;
      documentId: string;
      expectedRowVersion: number;
    }): Promise<KycDocumentReference> =>
      unwrap(
        await api.PUT("/api/v1/kyc-cases/{kyc_id}/document-references", {
          params: { path: { kyc_id: kycId } },
          body: {
            purpose,
            document_id: documentId,
            expected_row_version: expectedRowVersion,
          },
        }),
      ),
  );
}

export function useCreateKycAppointment() {
  return useKycMutation(
    async ({
      kycId,
      expectedRowVersion,
      dueAt,
      reminderAt,
      assignedAgentId,
      description,
    }: {
      kycId: string;
      expectedRowVersion: number;
      dueAt: string;
      reminderAt?: string | null;
      assignedAgentId?: string | null;
      description?: string | null;
    }): Promise<KycAppointment> =>
      unwrap(
        await api.POST("/api/v1/kyc-cases/{kyc_id}/appointments", {
          params: { path: { kyc_id: kycId } },
          body: {
            idempotency_key: crypto.randomUUID(),
            expected_row_version: expectedRowVersion,
            due_at: dueAt,
            reminder_at: reminderAt ?? null,
            assigned_agent_id: assignedAgentId ?? null,
            description: description?.trim() || null,
          },
        }),
      ),
  );
}

function useKycDecision(managerApproval: boolean) {
  return useKycMutation(
    async ({
      kycId,
      expectedRowVersion,
      decision,
      reasonCode,
      reason,
    }: {
      kycId: string;
      expectedRowVersion: number;
      decision: "approved" | "rejected" | "needs_information";
      reasonCode?: KycReasonCode | null;
      reason?: string | null;
    }): Promise<KycDecision> => {
      const params = { path: { kyc_id: kycId } };
      const body = {
        idempotency_key: crypto.randomUUID(),
        expected_row_version: expectedRowVersion,
        decision,
        reason_code: reasonCode ?? null,
        reason: reason?.trim() || null,
      };
      return unwrap(
        managerApproval
          ? await api.POST("/api/v1/kyc-cases/{kyc_id}/approvals", { params, body })
          : await api.POST("/api/v1/kyc-cases/{kyc_id}/decisions", { params, body }),
      );
    },
  );
}

export const useRecordKycReview = () => useKycDecision(false);
export const useRecordKycApproval = () => useKycDecision(true);
