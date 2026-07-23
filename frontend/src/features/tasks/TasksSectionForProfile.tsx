import { useState } from "react";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useTasks } from "@/features/tasks/api";
import { TaskActions } from "@/features/tasks/TaskActions";
import {
  TaskDue,
  TaskPriorityChip,
  TaskStatusChip,
  TaskTypeChip,
} from "@/features/tasks/TaskBadges";
import { TaskForm } from "@/features/tasks/TaskForm";
import type { Task } from "@/features/tasks/types";

const PROFILE_PAGE_SIZE = 20;

function TaskLine({ task, onEdit }: { task: Task; onEdit: (task: Task) => void }): JSX.Element {
  return (
    <li className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-border px-3 py-2">
      <div className="min-w-0">
        <button
          type="button"
          onClick={() => onEdit(task)}
          className="truncate text-left text-sm font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          {task.title}
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-1 text-xs">
          <TaskTypeChip value={task.task_type} />
          <TaskPriorityChip value={task.priority} />
          {task.status === "open" ? <TaskDue task={task} /> : <TaskStatusChip value={task.status} />}
        </div>
        {task.assigned_agent_name ? (
          <p className="mt-1 text-xs text-text-secondary">{task.assigned_agent_name}</p>
        ) : null}
      </div>
      {/* The profile already links the customer — only the lifecycle actions are useful here. */}
      <TaskActions task={task} showLinks={false} />
    </li>
  );
}

/**
 * Customer Profile task section (Doc 14 §9) — open tasks sorted by due date with inline actions,
 * completed tasks collapsed, and inline create pre-bound to this contact. Task lifecycle already
 * flows into the existing `TimelineSection` through the `contact_events` projection, so no separate
 * task timeline is built here.
 */
export function TasksSectionForProfile({ contactId }: { contactId: string }): JSX.Element {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);

  const open = useTasks({
    contact_id: contactId,
    status: ["open"],
    sort: "due_at",
    limit: PROFILE_PAGE_SIZE,
  });
  const completed = useTasks(
    {
      contact_id: contactId,
      status: ["completed"],
      sort: "-completed_at",
      limit: PROFILE_PAGE_SIZE,
    },
    showCompleted,
  );

  const openRows = open.data?.data ?? [];
  const completedRows = completed.data?.data ?? [];

  return (
    <Section
      title="Tasks"
      action={
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover"
        >
          New task
        </button>
      }
    >
      {open.isLoading ? (
        <Spinner label="Loading tasks…" />
      ) : open.isError ? (
        <ErrorState message={apiErrorMessage(open.error)} onRetry={() => void open.refetch()} />
      ) : openRows.length === 0 ? (
        <EmptyState title="No open tasks" description="Create a follow-up to keep this lead moving." />
      ) : (
        <ul className="space-y-2">
          {openRows.map((task) => (
            <TaskLine key={task.id} task={task} onEdit={setEditing} />
          ))}
        </ul>
      )}

      <div className="mt-3 border-t border-border pt-3">
        <button
          type="button"
          onClick={() => setShowCompleted((shown) => !shown)}
          aria-expanded={showCompleted}
          className="text-xs text-accent hover:underline"
        >
          {showCompleted ? "Hide completed tasks" : "Show completed tasks"}
        </button>

        {showCompleted ? (
          <div className="mt-2">
            {completed.isLoading ? (
              <Spinner label="Loading completed tasks…" />
            ) : completed.isError ? (
              <ErrorState
                message={apiErrorMessage(completed.error)}
                onRetry={() => void completed.refetch()}
              />
            ) : completedRows.length === 0 ? (
              <EmptyState title="No completed tasks" />
            ) : (
              <ul className="space-y-2">
                {completedRows.map((task) => (
                  <TaskLine key={task.id} task={task} onEdit={setEditing} />
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>

      {creating ? <TaskForm contactId={contactId} onClose={() => setCreating(false)} /> : null}
      {editing ? <TaskForm task={editing} onClose={() => setEditing(null)} /> : null}
    </Section>
  );
}
