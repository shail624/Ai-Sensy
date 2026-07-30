import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  AttributeDefinition,
  Campaign,
  CampaignCreateRequest,
  CampaignDispatch,
  CampaignEstimate,
  CampaignPreview,
  CampaignProgress,
  CampaignRetry,
  CampaignScheduleRequest,
  CampaignScheduleResult,
  CampaignState,
  CampaignUpdateRequest,
  PhoneNumber,
  RecipientsPage,
  Segment,
  Tag,
  Template,
} from "@/features/campaigns/types";

// Shared error helper, re-exported for this feature's components (as tasks and customer-profile do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const campaignKeys = {
  all: ["campaigns"] as const,
  list: () => ["campaigns", "list"] as const,
  detail: (id: string) => ["campaigns", "detail", id] as const,
  progress: (id: string) => ["campaigns", "progress", id] as const,
  recipients: (id: string) => ["campaigns", "recipients", id] as const,
  preview: (id: string) => ["campaigns", "preview", id] as const,
  estimate: (id: string) => ["campaigns", "estimate", id] as const,
  pickers: () => ["campaigns", "pickers"] as const,
};

/**
 * Every campaign in the organization, newest first.
 *
 * `GET /campaigns` declares **no** query parameters in the contract — the endpoint reads `q` and
 * `status` straight off `request.query_params`, so they are invisible to OpenAPI and unreachable
 * from the generated client, and it returns the org's complete list with no server-side paging.
 * Search, filtering, sorting and pagination therefore run in the client over that complete set
 * (`selectors.ts`), which is exact rather than approximate. `useContactSearch` solved the same
 * problem by switching to an endpoint that *does* declare its query; campaigns has no such
 * endpoint, and inventing untyped parameters here would mean hand-writing contract shape.
 */
export function useCampaigns(enabled = true) {
  return useQuery({
    queryKey: campaignKeys.list(),
    queryFn: async (): Promise<Campaign[]> =>
      unwrap(await api.GET("/api/v1/campaigns")).data,
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useCampaign(campaignId: string, enabled = true) {
  return useQuery({
    queryKey: campaignKeys.detail(campaignId),
    queryFn: async (): Promise<Campaign> =>
      unwrap(
        await api.GET("/api/v1/campaigns/{campaign_id}", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
    enabled: enabled && Boolean(campaignId),
  });
}

/**
 * Live send progress, derived server-side from the roster (FR-CAM-10). Polled only while the
 * campaign can still move: a finished campaign's numbers never change again, so polling it would
 * be a request per interval for a constant answer.
 */
export function useCampaignProgress(campaignId: string, live: boolean) {
  return useQuery({
    queryKey: campaignKeys.progress(campaignId),
    queryFn: async (): Promise<CampaignProgress> =>
      unwrap(
        await api.GET("/api/v1/campaigns/{campaign_id}/progress", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
    enabled: Boolean(campaignId),
    refetchInterval: live ? 5000 : false,
  });
}

/**
 * The first page of the per-recipient ledger (FR-CAM-10).
 *
 * The endpoint pages at a fixed 50 and accepts `cursor`/`status`, but — as with the list — reads
 * them off `request.query_params`, so neither reaches the generated client. This returns the one
 * page the contract exposes and the UI says so plainly when `has_more` is true, rather than
 * rendering pagination controls that cannot advance.
 */
export function useCampaignRecipients(campaignId: string, enabled = true) {
  return useQuery({
    queryKey: campaignKeys.recipients(campaignId),
    queryFn: async (): Promise<RecipientsPage> =>
      unwrap(
        await api.GET("/api/v1/campaigns/{campaign_id}/recipients", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
    enabled: enabled && Boolean(campaignId),
  });
}

/**
 * Audience size + sample renders. A POST that reads the materialized roster and writes nothing —
 * `campaigns:read` — so it is modelled as a query and fetched only when its surface is open.
 */
export function useCampaignPreview(campaignId: string, enabled: boolean) {
  return useQuery({
    queryKey: campaignKeys.preview(campaignId),
    queryFn: async (): Promise<CampaignPreview> =>
      unwrap(
        await api.POST("/api/v1/campaigns/{campaign_id}/preview", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
    enabled: enabled && Boolean(campaignId),
  });
}

/**
 * Pre-send cost from the rate card (FR-CAM-11). `enabled` is deliberate: the estimate caches its
 * quote on the campaign row, and an empty rate card answers 422 `rate_card_not_configured`, so it
 * fires when the operator asks for a cost — not on every detail render.
 */
export function useCampaignEstimate(campaignId: string, enabled: boolean) {
  return useQuery({
    queryKey: campaignKeys.estimate(campaignId),
    queryFn: async (): Promise<CampaignEstimate> =>
      unwrap(
        await api.POST("/api/v1/campaigns/{campaign_id}/estimate-cost", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
    enabled: enabled && Boolean(campaignId),
    retry: false,
  });
}

/** Every campaign mutation shifts the list, the detail and the progress numbers together. */
function useCampaignMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all });
    },
  });
}

export function useCreateCampaign() {
  return useCampaignMutation(
    async (body: CampaignCreateRequest): Promise<Campaign> =>
      unwrap(await api.POST("/api/v1/campaigns", { body })),
  );
}

export function useUpdateCampaign() {
  return useCampaignMutation(
    async ({
      campaignId,
      body,
    }: {
      campaignId: string;
      body: CampaignUpdateRequest;
    }): Promise<Campaign> =>
      unwrap(
        await api.PATCH("/api/v1/campaigns/{campaign_id}", {
          params: { path: { campaign_id: campaignId } },
          body,
        }),
      ),
  );
}

export function useDeleteCampaign() {
  return useCampaignMutation(async (campaignId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/campaigns/{campaign_id}", {
      params: { path: { campaign_id: campaignId } },
    });
    if (error !== undefined) throw error;
  });
}

export function useDispatchCampaign() {
  return useCampaignMutation(
    async (campaignId: string): Promise<CampaignDispatch> =>
      unwrap(
        await api.POST("/api/v1/campaigns/{campaign_id}/dispatch", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
  );
}

export function useScheduleCampaign() {
  return useCampaignMutation(
    async ({
      campaignId,
      body,
    }: {
      campaignId: string;
      body: CampaignScheduleRequest;
    }): Promise<CampaignScheduleResult> =>
      unwrap(
        await api.POST("/api/v1/campaigns/{campaign_id}/schedule", {
          params: { path: { campaign_id: campaignId } },
          body,
        }),
      ),
  );
}

/** Pause, resume and cancel share one response shape (`CampaignStateResponse`, Doc 04 §17). */
function useStateAction(action: "pause" | "resume" | "cancel") {
  return useCampaignMutation(async (campaignId: string): Promise<CampaignState> => {
    const params = { path: { campaign_id: campaignId } };
    if (action === "pause") {
      return unwrap(await api.POST("/api/v1/campaigns/{campaign_id}/pause", { params }));
    }
    if (action === "resume") {
      return unwrap(await api.POST("/api/v1/campaigns/{campaign_id}/resume", { params }));
    }
    return unwrap(await api.POST("/api/v1/campaigns/{campaign_id}/cancel", { params }));
  });
}

export const usePauseCampaign = () => useStateAction("pause");
export const useResumeCampaign = () => useStateAction("resume");
export const useCancelCampaign = () => useStateAction("cancel");

export function useRetryCampaign() {
  return useCampaignMutation(
    async (campaignId: string): Promise<CampaignRetry> =>
      unwrap(
        await api.POST("/api/v1/campaigns/{campaign_id}/retry", {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
  );
}

// --- Picker sources -----------------------------------------------------------------------------
//
// The wizard *selects* a template, a number and an audience; it does not administer any of them.
// These are plain reads of existing list endpoints, cached under the feature's key so the wizard
// opens without re-fetching between steps.

export function useTemplates(enabled = true) {
  return useQuery({
    queryKey: [...campaignKeys.pickers(), "templates"],
    queryFn: async (): Promise<Template[]> =>
      unwrap(await api.GET("/api/v1/templates")).data,
    enabled,
  });
}

export function usePhoneNumbers(enabled = true) {
  return useQuery({
    queryKey: [...campaignKeys.pickers(), "phone-numbers"],
    queryFn: async (): Promise<PhoneNumber[]> =>
      unwrap(await api.GET("/api/v1/phone-numbers")).data,
    enabled,
  });
}

export function useSegments(enabled = true) {
  return useQuery({
    queryKey: [...campaignKeys.pickers(), "segments"],
    queryFn: async (): Promise<Segment[]> => unwrap(await api.GET("/api/v1/segments")),
    enabled,
  });
}

export function useTags(enabled = true) {
  return useQuery({
    queryKey: [...campaignKeys.pickers(), "tags"],
    queryFn: async (): Promise<Tag[]> => unwrap(await api.GET("/api/v1/tags")),
    enabled,
  });
}

/** Custom-attribute definitions — the key vocabulary an `attribute` variable mapping selects from. */
export function useAttributeDefinitions(enabled = true) {
  return useQuery({
    queryKey: [...campaignKeys.pickers(), "attributes"],
    queryFn: async (): Promise<AttributeDefinition[]> =>
      unwrap(await api.GET("/api/v1/custom-attributes")),
    enabled,
  });
}
