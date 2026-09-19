import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  JobAccepted,
  PreviewValues,
  Template,
  TemplateCreateRequest,
  TemplatePreview,
  TemplateUpdateRequest,
  TemplateUsage,
  TemplateVersion,
  Waba,
} from "@/features/templates/types";

// Shared error helper, re-exported for this feature's components (as tasks and campaigns do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const templateKeys = {
  all: ["templates"] as const,
  list: () => ["templates", "list"] as const,
  detail: (id: string) => ["templates", "detail", id] as const,
  preview: (id: string, values?: unknown) => ["templates", "preview", id, values] as const,
  versions: (id: string) => ["templates", "versions", id] as const,
  wabas: () => ["templates", "wabas"] as const,
  usage: ["templates", "usage"] as const,
};

/**
 * Every template in the organization.
 *
 * `GET /templates` declares **no** query parameters in the contract — the endpoint reads `q`,
 * `status`, `category`, `language` and `waba` straight off `request.query_params`, so none of them
 * is visible to OpenAPI or reachable from the generated client, and it returns the complete list
 * with no server-side paging. Search, filtering, sorting and pagination therefore run in the client
 * over that complete set (`selectors.ts`), which is exact rather than approximate. The alternative
 * — passing parameters the contract does not declare — would mean hand-writing contract shape.
 */
export function useTemplates(enabled = true) {
  return useQuery({
    queryKey: templateKeys.list(),
    queryFn: async (): Promise<Template[]> => unwrap(await api.GET("/api/v1/templates")).data,
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useTemplate(templateId: string, enabled = true) {
  return useQuery({
    queryKey: templateKeys.detail(templateId),
    queryFn: async (): Promise<Template> =>
      unwrap(
        await api.GET("/api/v1/templates/{template_id}", {
          params: { path: { template_id: templateId } },
        }),
      ),
    enabled: enabled && Boolean(templateId),
  });
}

/**
 * The server's own render of the template (FR-TPL-08) — a pure projection that stores nothing and
 * sends nothing.
 *
 * Sample values are optional. With none, the renderer leaves every placeholder visible on purpose
 * — "a preview must not invent a value" — so what comes back is the template as written. With
 * them, it is one customer's actual message, which is the thing worth checking before a send goes
 * to everybody at once.
 */
export function useTemplatePreview(
  templateId: string,
  values?: PreviewValues,
  enabled = true,
) {
  // Blanks are dropped rather than sent: an empty value would substitute an empty string into the
  // message and produce a plausible-looking result for a variable nobody supplied. Left out, the
  // renderer keeps the placeholder visible, which is what tells an operator the mapping is short.
  const query = {
    ...(values?.header.some(Boolean) ? { header: values.header.filter(Boolean) } : {}),
    ...(values?.body.some(Boolean) ? { body: values.body.filter(Boolean) } : {}),
    ...(values?.buttons.some(Boolean) ? { button: values.buttons.filter(Boolean) } : {}),
  };
  return useQuery({
    queryKey: templateKeys.preview(templateId, query),
    queryFn: async (): Promise<TemplatePreview> =>
      unwrap(
        await api.GET("/api/v1/templates/{template_id}/preview", {
          params: { path: { template_id: templateId }, query },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled: enabled && Boolean(templateId),
  });
}

/** Version history — every submitted definition, newest last (Doc 03 §7.2). */
export function useTemplateVersions(templateId: string, enabled: boolean) {
  return useQuery({
    queryKey: templateKeys.versions(templateId),
    queryFn: async (): Promise<TemplateVersion[]> =>
      unwrap(
        await api.GET("/api/v1/templates/{template_id}/versions", {
          params: { path: { template_id: templateId } },
        }),
      ).data,
    enabled: enabled && Boolean(templateId),
  });
}

/** WABAs — the account a new template is created against. Selection only, not administration. */
export function useWabas(enabled = true) {
  return useQuery({
    queryKey: templateKeys.wabas(),
    queryFn: async (): Promise<Waba[]> => unwrap(await api.GET("/api/v1/waba")).data,
    enabled,
  });
}

/** Every template mutation shifts the list, the detail, the render and the history together. */
function useTemplateMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: templateKeys.all });
    },
  });
}

/**
 * Create, and — unless held as a draft — submit to Meta.
 *
 * `submit` is what separates "save a draft" from "ask Meta", and it matters: creating with
 * `submit: true` is a round trip, so a channel failure surfaces as a 502 rather than a 422.
 */
export function useCreateTemplate() {
  return useTemplateMutation(
    async (body: TemplateCreateRequest): Promise<Template> =>
      unwrap(await api.POST("/api/v1/templates", { body })),
  );
}

export function useUpdateTemplate() {
  return useTemplateMutation(
    async ({
      templateId,
      body,
    }: {
      templateId: string;
      body: TemplateUpdateRequest;
    }): Promise<Template> =>
      unwrap(
        await api.PATCH("/api/v1/templates/{template_id}", {
          params: { path: { template_id: templateId } },
          body,
        }),
      ),
  );
}

/** Withdraws from Meta first, then soft-deletes locally — so the registry never lies about it. */
export function useDeleteTemplate() {
  return useTemplateMutation(async (templateId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/templates/{template_id}", {
      params: { path: { template_id: templateId } },
    });
    if (error !== undefined) throw error;
  });
}

/**
 * Reconcile templates and approval statuses from Meta (FR-TPL-01).
 *
 * Async by contract: the call answers 202 with a job envelope and nothing talks to Meta on the
 * request path, because reconciling a WABA's templates cannot block a request.
 */
export function useSyncTemplates() {
  return useTemplateMutation(
    async (): Promise<JobAccepted> => unwrap(await api.POST("/api/v1/templates/sync")),
  );
}

/**
 * How each template has actually performed.
 *
 * Aggregates only, so this is a template read rather than a campaign one. Kept out of
 * `useTemplates` because the list renders fine without it and a slower query should not hold up
 * the screen an operator opens to write a template.
 */
export function useTemplateUsage(enabled = true) {
  return useQuery({
    queryKey: templateKeys.usage,
    queryFn: async (): Promise<TemplateUsage[]> =>
      unwrap(await api.GET("/api/v1/templates/usage")).data,
    enabled,
  });
}
