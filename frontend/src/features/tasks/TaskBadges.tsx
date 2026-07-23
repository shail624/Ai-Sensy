import type { Task, TaskPriority, TaskStatus, TaskType } from "@/features/tasks/types";
import {
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
  TASK_TYPE_LABELS,
} from "@/features/tasks/types";

const PRIORITY_TONE: Record<TaskPriority, string> = {
  low: "border-border text-text-secondary",
  medium: "border-border text-text-primary",
  high: "border-warning text-warning",
  critical: "border-danger text-danger",
};

const STATUS_TONE: Record<TaskStatus, string> = {
  open: "border-border text-text-primary",
  completed: "border-success text-success",
  skipped: "border-border text-text-disabled",
  cancelled: "border-border text-text-disabled",
};

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

/** Start of the current day, local time — the boundary the server buckets on (Doc 14 §7.3). */
function startOfToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

export type DueTone = "overdue" | "today" | "future";

export function dueTone(task: Task): DueTone {
  if (task.status !== "open") return "future";
  const due = new Date(task.due_at);
  const start = startOfToday();
  if (due < start) return "overdue";
  const endOfToday = new Date(start.getTime() + 86_400_000);
  return due < endOfToday ? "today" : "future";
}

/** Due date, or date + time when the task carries one (`has_time`, FR-TASK-05). */
export function formatDue(task: Task): string {
  const due = new Date(task.due_at);
  return task.has_time ? due.toLocaleString() : due.toLocaleDateString();
}

export function TaskTypeChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip("border-border text-text-secondary")}>
      {TASK_TYPE_LABELS[value as TaskType] ?? value}
    </span>
  );
}

export function TaskPriorityChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(PRIORITY_TONE[value as TaskPriority] ?? "border-border")}>
      {TASK_PRIORITY_LABELS[value as TaskPriority] ?? value}
    </span>
  );
}

export function TaskStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(STATUS_TONE[value as TaskStatus] ?? "border-border")}>
      {TASK_STATUS_LABELS[value as TaskStatus] ?? value}
    </span>
  );
}

/** The due moment with an overdue/due-today badge — shared by the table and the work queue. */
export function TaskDue({ task }: { task: Task }): JSX.Element {
  const tone = dueTone(task);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-text-secondary">{formatDue(task)}</span>
      {tone === "overdue" ? (
        <span className={chip("border-danger text-danger")}>Overdue</span>
      ) : tone === "today" ? (
        <span className={chip("border-warning text-warning")}>Due today</span>
      ) : null}
    </span>
  );
}
