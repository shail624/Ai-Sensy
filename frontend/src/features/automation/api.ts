import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AutomationCreateRequest,
  AutomationFlow,
  AutomationStatus,
  AutomationUpdateRequest,
  AutomationValidation,
  AutomationVersion,
} from "@/features/automation/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export const automationKeys = {
  all: ["automations"] as const,
  list: (q: string, status: AutomationStatus | "all") => ["automations", "list", q, status] as const,
  detail: (id: string) => ["automations", "detail", id] as const,
  versions: (id: string) => ["automations", "versions", id] as const,
};

export function useAutomations(q: string, status: AutomationStatus | "all") {
  return useQuery({
    queryKey: automationKeys.list(q, status),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/automations", {
          params: { query: { q: q || undefined, status: status === "all" ? undefined : [status], limit: 200 } },
        }),
      ),
  });
}

export function useAutomation(id: string | null) {
  return useQuery({
    queryKey: automationKeys.detail(id ?? ""),
    queryFn: async (): Promise<AutomationFlow> =>
      unwrap(
        await api.GET("/api/v1/automations/{automation_id}", {
          params: { path: { automation_id: id! } },
        }),
      ),
    enabled: Boolean(id),
  });
}

export function useAutomationVersions(id: string | null) {
  return useQuery({
    queryKey: automationKeys.versions(id ?? ""),
    queryFn: async (): Promise<AutomationVersion[]> =>
      unwrap(
        await api.GET("/api/v1/automations/{automation_id}/versions", {
          params: { path: { automation_id: id! } },
        }),
      ).data,
    enabled: Boolean(id),
  });
}

function useAutomationMutation<TVariables>(
  mutationFn: (variables: TVariables) => Promise<AutomationFlow>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (flow) => {
      queryClient.setQueryData(automationKeys.detail(flow.id), flow);
      void queryClient.invalidateQueries({ queryKey: automationKeys.all });
      void queryClient.invalidateQueries({ queryKey: automationKeys.versions(flow.id) });
      void queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

export function useCreateAutomation() {
  return useAutomationMutation(
    async (body: AutomationCreateRequest) => unwrap(await api.POST("/api/v1/automations", { body })),
  );
}

export function useUpdateAutomation(id: string) {
  return useAutomationMutation(
    async (body: AutomationUpdateRequest) =>
      unwrap(
        await api.PATCH("/api/v1/automations/{automation_id}", {
          params: { path: { automation_id: id } }, body,
        }),
      ),
  );
}

export function useValidateAutomation(id: string) {
  return useMutation({
    mutationFn: async (): Promise<AutomationValidation> =>
      unwrap(
        await api.POST("/api/v1/automations/{automation_id}/validate", {
          params: { path: { automation_id: id } },
        }),
      ),
  });
}

function useGuardedMutation(id: string, operation: "publish" | "disable" | "enable") {
  return useAutomationMutation(async (rowVersion: number) => {
    const body = { expected_row_version: rowVersion };
    if (operation === "publish") {
      return unwrap(await api.POST("/api/v1/automations/{automation_id}/publish", { params: { path: { automation_id: id } }, body }));
    }
    if (operation === "disable") {
      return unwrap(await api.POST("/api/v1/automations/{automation_id}/disable", { params: { path: { automation_id: id } }, body }));
    }
    return unwrap(await api.POST("/api/v1/automations/{automation_id}/enable", { params: { path: { automation_id: id } }, body }));
  });
}

export function usePublishAutomation(id: string) { return useGuardedMutation(id, "publish"); }
export function useDisableAutomation(id: string) { return useGuardedMutation(id, "disable"); }
export function useEnableAutomation(id: string) { return useGuardedMutation(id, "enable"); }

export function useRestoreAutomation(id: string) {
  return useAutomationMutation(
    async ({ versionNo, rowVersion }: { versionNo: number; rowVersion: number }) =>
      unwrap(
        await api.POST("/api/v1/automations/{automation_id}/versions/{version_no}/restore", {
          params: { path: { automation_id: id, version_no: versionNo } },
          body: { expected_row_version: rowVersion },
        }),
      ),
  );
}
