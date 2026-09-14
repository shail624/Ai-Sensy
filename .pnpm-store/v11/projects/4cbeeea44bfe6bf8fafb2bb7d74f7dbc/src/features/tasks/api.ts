import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth";
import type {
  Task,
  TaskBulkResult,
  TaskCreateRequest,
  TaskListQuery,
  TaskStats,
  TasksPage,
  TaskUpdateRequest,
} from "@/features/tasks/types";

// Shared error helper, re-exported for this feature's components (as customer-profile does).
export { apiErrorMessage } from "@/lib/api/errors";

type Me = components["schemas"]["MeResponse"];

export const taskKeys = {
  all: ["tasks"] as const,
  list: (query: TaskListQuery) => ["tasks", "list", query] as const,
  stats: (assigneeId?: string) => ["tasks", "stats", assigneeId ?? "me"] as const,
};

/**
 * The signed-in user — the identity behind the "Assigned to me"/"Assigned by me" presets and the
 * work queue (Doc 14 §10/§11). The session is owned by `AuthProvider`; this adapter keeps the
 * feature's call sites unchanged while there is exactly one source of identity truth.
 */
export function useCurrentUser(): { data: Me | null; isLoading: boolean; isError: boolean; error: unknown; refetch: () => void } {
  const { user, status } = useAuth();
  return {
    data: user,
    isLoading: status === "loading",
    isError: false,
    error: null,
    refetch: () => undefined,
  };
}

export { useHasPermission } from "@/lib/auth";

/**
 * A filtered, bucketed, cursor-paginated page of tasks (Doc 14 §7.2). `keepPreviousData` holds the
 * table steady while a new page or filter resolves, exactly as `useContactSearch` does.
 */
export function useTasks(query: TaskListQuery, enabled = true) {
  return useQuery({
    queryKey: taskKeys.list(query),
    queryFn: async (): Promise<TasksPage> =>
      unwrap(await api.GET("/api/v1/tasks", { params: { query } })),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** Work-queue counts for the widget's header badges — one cheap call (Doc 14 §11). */
export function useTaskStats(assigneeId?: string) {
  return useQuery({
    queryKey: taskKeys.stats(assigneeId),
    queryFn: async (): Promise<TaskStats> =>
      unwrap(
        await api.GET("/api/v1/tasks/stats", {
          params: { query: assigneeId ? { assignee_id: assigneeId } : {} },
        }),
      ),
    enabled: assigneeId !== undefined ? Boolean(assigneeId) : true,
  });
}

/** Every task mutation invalidates the whole feature: lists, buckets and stats all shift together. */
function useTaskMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: taskKeys.all });
    },
  });
}

export function useCreateTask() {
  return useTaskMutation(
    async (body: TaskCreateRequest): Promise<Task> =>
      unwrap(await api.POST("/api/v1/tasks", { body })),
  );
}

export function useUpdateTask() {
  return useTaskMutation(
    async ({ taskId, body }: { taskId: string; body: TaskUpdateRequest }): Promise<Task> =>
      unwrap(
        await api.PATCH("/api/v1/tasks/{task_id}", {
          params: { path: { task_id: taskId } },
          body,
        }),
      ),
  );
}

export function useCompleteTask() {
  return useTaskMutation(
    async ({
      taskId,
      completionNotes,
      createTimelineNote = false,
      expectedRowVersion,
    }: {
      taskId: string;
      completionNotes?: string | null;
      createTimelineNote?: boolean;
      expectedRowVersion?: number;
    }): Promise<Task> =>
      unwrap(
        await api.POST("/api/v1/tasks/{task_id}/complete", {
          params: { path: { task_id: taskId } },
          body: {
            completion_notes: completionNotes ?? null,
            create_timeline_note: createTimelineNote,
            expected_row_version: expectedRowVersion,
          },
        }),
      ),
  );
}

/** Skip and cancel share one request body (`TaskReasonRequest`, Doc 14 §8). */
function useReasonAction(action: "skip" | "cancel") {
  return useTaskMutation(
    async ({ taskId, reason, expectedRowVersion }: { taskId: string; reason?: string | null; expectedRowVersion?: number }): Promise<Task> => {
      const path = { path: { task_id: taskId } };
      const body = { reason: reason ?? null, expected_row_version: expectedRowVersion };
      return unwrap(
        action === "skip"
          ? await api.POST("/api/v1/tasks/{task_id}/skip", { params: path, body })
          : await api.POST("/api/v1/tasks/{task_id}/cancel", { params: path, body }),
      );
    },
  );
}

export const useSkipTask = () => useReasonAction("skip");
export const useCancelTask = () => useReasonAction("cancel");

export function useReopenTask() {
  return useTaskMutation(
    async (taskId: string): Promise<Task> =>
      unwrap(
        await api.POST("/api/v1/tasks/{task_id}/reopen", {
          params: { path: { task_id: taskId } },
          body: {},
        }),
      ),
  );
}

export function useRescheduleTask() {
  return useTaskMutation(
    async ({
      taskId,
      dueAt,
      hasTime,
      expectedRowVersion,
    }: {
      taskId: string;
      dueAt: string;
      hasTime?: boolean;
      expectedRowVersion?: number;
    }): Promise<Task> =>
      unwrap(
        await api.POST("/api/v1/tasks/{task_id}/reschedule", {
          params: { path: { task_id: taskId } },
          body: { due_at: dueAt, has_time: hasTime ?? true, expected_row_version: expectedRowVersion },
        }),
      ),
  );
}

export function useSnoozeTask() {
  return useTaskMutation(
    async ({ taskId, minutes, expectedRowVersion }: { taskId: string; minutes: number; expectedRowVersion?: number }): Promise<Task> =>
      unwrap(
        await api.POST("/api/v1/tasks/{task_id}/snooze", {
          params: { path: { task_id: taskId } },
          body: { minutes, expected_row_version: expectedRowVersion },
        }),
      ),
  );
}

export function useReassignTask() {
  return useTaskMutation(
    async ({ taskId, assignedAgentId }: { taskId: string; assignedAgentId: string }): Promise<Task> =>
      unwrap(
        await api.POST("/api/v1/tasks/{task_id}/reassign", {
          params: { path: { task_id: taskId } },
          body: { assigned_agent_id: assignedAgentId },
        }),
      ),
  );
}

export function useDeleteTask() {
  return useTaskMutation(async (taskId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/tasks/{task_id}", {
      params: { path: { task_id: taskId } },
    });
    if (error !== undefined) throw error;
  });
}

type BulkSet = Omit<components["schemas"]["TaskBulkUpdateRequest"], "task_ids">;

export function useBulkUpdateTasks() {
  return useTaskMutation(
    async ({ taskIds, set }: { taskIds: string[]; set: BulkSet }): Promise<TaskBulkResult> =>
      unwrap(
        await api.POST("/api/v1/tasks/bulk-update", { body: { task_ids: taskIds, ...set } }),
      ),
  );
}

export function useBulkDeleteTasks() {
  return useTaskMutation(
    async (taskIds: string[]): Promise<TaskBulkResult> =>
      unwrap(await api.POST("/api/v1/tasks/bulk-delete", { body: { task_ids: taskIds } })),
  );
}
