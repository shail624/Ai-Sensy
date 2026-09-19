import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  ActivationRecord,
  ActivationStatus,
  SimOrder,
  SimOrderEvent,
  SimStatus,
} from "@/features/fulfilment/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const fulfilmentKeys = {
  all: ["fulfilment"] as const,
  simOrders: ["fulfilment", "sim-orders"] as const,
  simEvents: (orderId: string) => ["fulfilment", "sim-events", orderId] as const,
  activations: ["fulfilment", "activations"] as const,
};

/** Every SIM order in the organization, newest first as the API returns them. */
export function useSimOrders(enabled = true) {
  return useQuery({
    queryKey: fulfilmentKeys.simOrders,
    queryFn: async (): Promise<SimOrder[]> => unwrap(await api.GET("/api/v1/sim-orders")).data,
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** One order's history — what happened to it and when, which is the answer to "why is it stuck". */
export function useSimOrderEvents(orderId: string | null) {
  return useQuery({
    queryKey: fulfilmentKeys.simEvents(orderId ?? ""),
    queryFn: async (): Promise<SimOrderEvent[]> =>
      unwrap(
        await api.GET("/api/v1/sim-orders/{order_id}/events", {
          params: { path: { order_id: orderId! } },
        }),
      ).data,
    enabled: Boolean(orderId),
  });
}

export function useActivationRecords(enabled = true) {
  return useQuery({
    queryKey: fulfilmentKeys.activations,
    queryFn: async (): Promise<ActivationRecord[]> =>
      unwrap(await api.GET("/api/v1/activation-records")).data,
    placeholderData: keepPreviousData,
    enabled,
  });
}

/**
 * Move one order on.
 *
 * `expected_row_version` is the server's optimistic-concurrency check and is sent from the row the
 * operator actually looked at: two people working the same queue is the normal case here, and the
 * second one must be told the order moved rather than quietly overwriting the first.
 *
 * `idempotency_key` is generated per attempt, so a retried request is the same transition rather
 * than a second one.
 */
export function useTransitionSimOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      order,
      to,
    }: {
      order: SimOrder;
      to: SimStatus;
    }): Promise<SimOrder> =>
      unwrap(
        await api.POST("/api/v1/sim-orders/{order_id}/transition", {
          params: { path: { order_id: order.id } },
          body: {
            to_status: to,
            expected_row_version: order.row_version,
            idempotency_key: crypto.randomUUID(),
          },
        }),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: fulfilmentKeys.all }),
  });
}

export function useTransitionActivation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      record,
      to,
    }: {
      record: ActivationRecord;
      to: ActivationStatus;
    }): Promise<ActivationRecord> =>
      unwrap(
        await api.POST("/api/v1/activation-records/{activation_id}/transition", {
          params: { path: { activation_id: record.id } },
          body: {
            to_status: to,
            expected_row_version: record.row_version,
            idempotency_key: crypto.randomUUID(),
          },
        }),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: fulfilmentKeys.all }),
  });
}
