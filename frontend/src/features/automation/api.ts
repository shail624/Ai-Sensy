import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AutomationCreateRequest,
  AutomationFlow,
  AutomationRun,
  AutomationStatus,
  AutomationTriggerReceipt,
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
  runs: (id: string) => ["automations", "runs", id] as const,
  run: (id: string) => ["automations", "run", id] as const,
  receipts: (id: string) => ["automations", "receipts", id] as const,
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

const ACTIVE_RUN_STATUSES = new Set(["queued", "running", "retrying"]);

export function useAutomationRuns(id: string | null) {
  return useQuery({
    queryKey: automationKeys.runs(id ?? ""),
    queryFn: async (): Promise<AutomationRun[]> =>
      unwrap(
        await api.GET("/api/v1/automations/{automation_id}/runs", {
          params: { path: { automation_id: id! }, query: { limit: 20 } },
        }),
      ).data,
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.some((run) => ACTIVE_RUN_STATUSES.has(run.status)) ? 1_000 : false,
  });
}

export function useAutomationRun(id: string | null) {
  return useQuery({
    queryKey: automationKeys.run(id ?? ""),
    queryFn: async (): Promise<AutomationRun> =>
      unwrap(
        await api.GET("/api/v1/automation-runs/{run_id}", {
          params: { path: { run_id: id! } },
        }),
      ),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data && ACTIVE_RUN_STATUSES.has(query.state.data.status) ? 750 : false,
  });
}

export function useAutomationTriggerReceipts(id: string | null) {
  return useQuery({
    queryKey: automationKeys.receipts(id ?? ""),
    queryFn: async (): Promise<AutomationTriggerReceipt[]> =>
      unwrap(
        await api.GET("/api/v1/automations/{automation_id}/trigger-receipts", {
          params: { path: { automation_id: id! }, query: { limit: 20 } },
        }),
      ).data,
    enabled: Boolean(id),
  });
}

export function useCreateAutomationTestRun(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ input, idempotencyKey }: { input: Record<string, unknown>; idempotencyKey: string }): Promise<AutomationRun> =>
      unwrap(
        await api.POST("/api/v1/automations/{automation_id}/test-runs", {
          params: {
            path: { automation_id: id },
            header: { "Idempotency-Key": idempotencyKey },
          },
          body: { input },
        }),
      ),
    onSuccess: (run) => {
      queryClient.setQueryData(automationKeys.run(run.id), run);
      void queryClient.invalidateQueries({ queryKey: automationKeys.runs(id) });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
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
