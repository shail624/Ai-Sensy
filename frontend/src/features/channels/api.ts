import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  JobAccepted,
  PhoneNumber,
  PhoneNumberHealth,
  PhoneNumberUpdateRequest,
  Waba,
  WabaCreateRequest,
  WabaUpdateRequest,
} from "@/features/channels/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const channelKeys = {
  all: ["channels"] as const,
  wabas: ["channels", "wabas"] as const,
  waba: (id: string) => ["channels", "wabas", id] as const,
  numbers: ["channels", "numbers"] as const,
  number: (id: string) => ["channels", "numbers", id] as const,
  health: (id: string) => ["channels", "numbers", id, "health"] as const,
};

/**
 * Every connected WABA, ordered by business name.
 *
 * `GET /waba` takes no parameters at all — not undeclared ones, none — and returns the complete
 * list for the organization. Search, filtering and sorting therefore run in the client over a set
 * that is genuinely complete, so nothing is hidden behind a page boundary here.
 */
export function useWabas() {
  return useQuery({
    queryKey: channelKeys.wabas,
    queryFn: async (): Promise<Waba[]> => unwrap(await api.GET("/api/v1/waba")).data,
  });
}

export function useWaba(wabaId: string, enabled = true) {
  return useQuery({
    queryKey: channelKeys.waba(wabaId),
    queryFn: async (): Promise<Waba> =>
      unwrap(
        await api.GET("/api/v1/waba/{waba_id}", { params: { path: { waba_id: wabaId } } }),
      ),
    enabled: enabled && Boolean(wabaId),
  });
}

/**
 * Every phone number in the organization.
 *
 * `GET /phone-numbers` accepts `filter[waba][eq]`, `filter[status][eq]` and
 * `filter[quality_rating][eq]`, but reads them off `request.query_params`, so none is declared in
 * the contract or reachable from the generated client. It applies **no limit**, so the response is
 * the complete set and client-side filtering is exact rather than a window onto it.
 */
export function useNumbers() {
  return useQuery({
    queryKey: channelKeys.numbers,
    queryFn: async (): Promise<PhoneNumber[]> =>
      unwrap(await api.GET("/api/v1/phone-numbers")).data,
  });
}

export function useNumber(numberId: string, enabled = true) {
  return useQuery({
    queryKey: channelKeys.number(numberId),
    queryFn: async (): Promise<PhoneNumber> =>
      unwrap(
        await api.GET("/api/v1/phone-numbers/{number_id}", {
          params: { path: { number_id: numberId } },
        }),
      ),
    enabled: enabled && Boolean(numberId),
  });
}

/**
 * Stored health for a number — quality, tier, throughput and the derived `healthy` verdict.
 *
 * Deliberately cheap: this reads what the last sync wrote and never calls Meta, so it is always
 * available even when the channel is not. `useRefreshNumber` is the one that goes out and asks.
 */
export function useNumberHealth(numberId: string, enabled = true) {
  return useQuery({
    queryKey: channelKeys.health(numberId),
    queryFn: async (): Promise<PhoneNumberHealth> =>
      unwrap(
        await api.GET("/api/v1/phone-numbers/{number_id}/health", {
          params: { path: { number_id: numberId } },
        }),
      ),
    enabled: enabled && Boolean(numberId),
  });
}

/** Any write here can move both lists — a sync adds numbers, a disconnect removes an account. */
function useChannelMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: channelKeys.all });
    },
  });
}

/**
 * Connect a WABA with its system-user token.
 *
 * The token is **write-only**: it is encrypted before it is persisted and no response model has a
 * field for it, so it can be sent and never read back. Meta's WABA id is globally unique, so
 * connecting one that is already known answers 409.
 */
export function useConnectWaba() {
  return useChannelMutation(
    async (body: WabaCreateRequest): Promise<Waba> =>
      unwrap(await api.POST("/api/v1/waba", { body })),
  );
}

/**
 * Amend a WABA's metadata, change its status, or rotate its token.
 *
 * One endpoint covers all three because they are one row. `row_version` rides along so a
 * concurrent change surfaces as the server's conflict rather than silently overwriting.
 */
export function useUpdateWaba() {
  return useChannelMutation(
    async ({ wabaId, body }: { wabaId: string; body: WabaUpdateRequest }): Promise<Waba> =>
      unwrap(
        await api.PATCH("/api/v1/waba/{waba_id}", {
          params: { path: { waba_id: wabaId } },
          body,
        }),
      ),
  );
}

/**
 * Disconnect a WABA.
 *
 * Refused while it still owns numbers (409). Note this is **not reversible from the platform**:
 * the row is soft-deleted but keeps Meta's globally unique WABA id, and the duplicate check
 * deliberately ignores soft-deletion — so the same account cannot be connected again.
 */
export function useDisconnectWaba() {
  return useChannelMutation(async (wabaId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/waba/{waba_id}", {
      params: { path: { waba_id: wabaId } },
    });
    if (error !== undefined) throw error;
  });
}

/**
 * Pull this account's phone numbers from Meta.
 *
 * Async by contract: the call answers 202 with a job envelope and nothing talks to Meta on the
 * request path, because reconciling numbers is a round trip that must not block a request.
 */
export function useSyncWaba() {
  return useChannelMutation(
    async (wabaId: string): Promise<JobAccepted> =>
      unwrap(
        await api.POST("/api/v1/waba/{waba_id}/sync", {
          params: { path: { waba_id: wabaId } },
        }),
      ),
  );
}

/**
 * Update the operator-owned fields of a number: its display name, its pacing limit, and whether it
 * is the default.
 *
 * Meta-owned facts — quality rating, messaging tier, throughput — are **not** settable, by design:
 * they arrive via sync, so letting them be typed here would create a value the next sync silently
 * undoes.
 */
export function useUpdateNumber() {
  return useChannelMutation(
    async ({
      numberId,
      body,
    }: {
      numberId: string;
      body: PhoneNumberUpdateRequest;
    }): Promise<PhoneNumber> =>
      unwrap(
        await api.PATCH("/api/v1/phone-numbers/{number_id}", {
          params: { path: { number_id: numberId } },
          body,
        }),
      ),
  );
}

/**
 * Re-pull a number's health and limits from Meta.
 *
 * This one does call the channel, so it fails as `502 channel_error` when Meta or the stored
 * credential is the problem — which is a different thing from the request being wrong, and is
 * surfaced as such.
 */
export function useRefreshNumber() {
  return useChannelMutation(
    async (numberId: string): Promise<PhoneNumberHealth> =>
      unwrap(
        await api.POST("/api/v1/phone-numbers/{number_id}/refresh", {
          params: { path: { number_id: numberId } },
        }),
      ),
  );
}
