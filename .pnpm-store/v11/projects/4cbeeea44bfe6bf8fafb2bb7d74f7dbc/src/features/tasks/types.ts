import type { components, operations } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2, §15).
export type Task = components["schemas"]["TaskResponse"];
export type TasksPage = components["schemas"]["TasksPage"];
export type TaskStats = components["schemas"]["TaskStatsResponse"];
export type TaskEvent = components["schemas"]["TaskEventResponse"];
export type TaskCreateRequest = components["schemas"]["TaskCreateRequest"];
export type TaskUpdateRequest = components["schemas"]["TaskUpdateRequest"];
export type TaskBulkResult = components["schemas"]["TaskBulkResultResponse"];

type ListQuery = NonNullable<operations["list_tasks_api_v1_tasks_get"]["parameters"]["query"]>;

export type TaskView = NonNullable<ListQuery["view"]>;
export type TaskSort = NonNullable<ListQuery["sort"]>;
export type TaskStatus = NonNullable<NonNullable<ListQuery["status"]>[number]>;
export type TaskType = NonNullable<NonNullable<ListQuery["type"]>[number]>;
export type TaskPriority = NonNullable<NonNullable<ListQuery["priority"]>[number]>;

/** The list-endpoint query, exactly as the contract declares it. */
export type TaskListQuery = ListQuery;

// --- Display labels for the wire enums (presentation only; values come from the contract) ------
export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  call: "Call",
  whatsapp: "WhatsApp",
  collect_documents: "Collect documents",
  verification: "Verification",
  reminder: "Reminder",
  meeting: "Meeting",
  custom: "Custom",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  open: "Open",
  completed: "Completed",
  skipped: "Skipped",
  cancelled: "Cancelled",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const TASK_TYPES = Object.keys(TASK_TYPE_LABELS) as TaskType[];
export const TASK_STATUSES = Object.keys(TASK_STATUS_LABELS) as TaskStatus[];
export const TASK_PRIORITIES = Object.keys(TASK_PRIORITY_LABELS) as TaskPriority[];

/** The six saved views of FR-TASK-10 — filter presets over the one list endpoint (Doc 14 §10). */
export interface TaskPreset {
  key: string;
  label: string;
  query: TaskListQuery;
}

export const TASK_PRESETS: TaskPreset[] = [
  { key: "today", label: "Today", query: { view: "today" } },
  { key: "overdue", label: "Overdue", query: { view: "overdue" } },
  { key: "upcoming", label: "Upcoming", query: { view: "upcoming" } },
  { key: "completed", label: "Completed", query: { status: ["completed"], sort: "-completed_at" } },
  { key: "assigned-to-me", label: "Assigned to me", query: {} },
  { key: "assigned-by-me", label: "Assigned by me", query: {} },
];
