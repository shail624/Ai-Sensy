import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ACTIVATION_AWAITING,
  KYC_AWAITING,
  activationToApproval,
  byWaitingLongest,
  kycToApproval,
  type ActivationRecord,
  type KycCase,
  type PendingApproval,
} from "@/features/approvals/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const approvalKeys = {
  all: ["approvals"] as const,
  pending: ["approvals", "pending"] as const,
};

/** A request that may legitimately fail for permission and must not take the others down. */
async function settle<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch {
    return fallback;
  }
}

/**
 * Everything waiting on a decision, from the modules that already own those decisions.
 *
 * Two sources, because two exist: KYC cases in `under_review` and activation records at `ready`.
 * Identity-merge recommendations are *not* here — they have an approve endpoint but no list
 * endpoint, so there is nothing to aggregate without inventing backend to fill a screen, which is
 * the wrong order to build in.
 */
export function usePendingApprovals(canKyc: boolean, canActivation: boolean) {
  return useQuery({
    queryKey: approvalKeys.pending,
    queryFn: async (): Promise<PendingApproval[]> => {
      const [kyc, activations] = await Promise.all([
        canKyc
          ? settle(
              (async () => unwrap(await api.GET("/api/v1/kyc-cases")).data)(),
              [] as KycCase[],
            )
          : ([] as KycCase[]),
        canActivation
          ? settle(
              (async () => unwrap(await api.GET("/api/v1/activation-records")).data)(),
              [] as ActivationRecord[],
            )
          : ([] as ActivationRecord[]),
      ]);
      return [
        ...kyc.filter((row) => row.status === KYC_AWAITING).map(kycToApproval),
        ...activations
          .filter((row) => row.status === ACTIVATION_AWAITING)
          .map(activationToApproval),
      ].sort(byWaitingLongest);
    },
  });
}

/**
 * Approve one item through the endpoint its own module owns.
 *
 * No shared approval route and no new authority: KYC goes to the KYC decision endpoint under
 * `kyc:approve`, activation to the activation approval endpoint under `activation:approve`. This
 * screen only gathers the work; each module still decides what approving means and who may do it.
 */
export function useApprove() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (item: PendingApproval): Promise<void> => {
      if (item.source === "kyc") {
        unwrap(
          await api.POST("/api/v1/kyc-cases/{kyc_id}/approvals", {
            params: { path: { kyc_id: item.id } },
            body: {
              decision: "approved",
              expected_row_version: item.rowVersion,
              idempotency_key: crypto.randomUUID(),
            },
          }),
        );
        return;
      }
      unwrap(
        await api.POST("/api/v1/activation-records/{activation_id}/approval", {
          params: { path: { activation_id: item.id } },
          body: {
            to_status: "approved",
            expected_row_version: item.rowVersion,
            idempotency_key: crypto.randomUUID(),
          },
        }),
      );
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: approvalKeys.all }),
  });
}
