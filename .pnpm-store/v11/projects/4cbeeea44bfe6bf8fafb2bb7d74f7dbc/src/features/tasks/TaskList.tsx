import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useBulkDeleteTasks,
  useBulkUpdateTasks,
  useCurrentUser,
  useTasks,
} from "@/features/tasks/api";
import { TaskFilters } from "@/features/tasks/TaskFilters";
import { TaskForm } from "@/features/tasks/TaskForm";
import { TaskTable } from "@/features/tasks/TaskTable";
import type { Task, TaskListQuery, TaskSort } from "@/features/tasks/types";
import { TASK_PRESETS } from "@/features/tasks/types";

const PAGE_SIZE = 25;
const BUTTON_CLASS = "rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50";

/** URL ⇄ query. The view preset, filters, sort and cursor all live in the address bar. */
function readQuery(params: URLSearchParams, meId: string | undefined): TaskListQuery {
  const preset = params.get("preset") ?? "today";
  const query: TaskListQuery = { limit: PAGE_SIZE };

  const found = TASK_PRESETS.find((entry) => entry.key === preset);
  if (found) Object.assign(query, found.query);
  if (meId) {
    if (preset === "assigned-by-me") query.assigned_by_id = meId;
    else if (preset !== "completed") query.assignee_id = meId;
  }

  const q = params.get("q");
  const status = params.get("status");
  const type = params.get("type");
  const priority = params.get("priority");
  const dueFrom = params.get("due_from");
  const dueTo = params.get("due_to");
  const sort = params.get("sort");
  const cursor = params.get("cursor");

  if (q) query.q = q;
  if (status) query.status = [status] as TaskListQuery["status"];
  if (type) query.type = [type] as TaskListQuery["type"];
  if (priority) query.priority = [priority] as TaskListQuery["priority"];
  if (dueFrom) query.due_from = dueFrom;
  if (dueTo) query.due_to = dueTo;
  if (sort) query.sort = sort as TaskSort;
  if (cursor) query.cursor = cursor;
  return query;
}

function writeQuery(preset: string, filters: TaskListQuery): URLSearchParams {
  const params = new URLSearchParams();
  params.set("preset", preset);
  if (filters.q) params.set("q", filters.q);
  if (filters.status?.[0]) params.set("status", filters.status[0]);
  if (filters.type?.[0]) params.set("type", filters.type[0]);
  if (filters.priority?.[0]) params.set("priority", filters.priority[0]);
  if (filters.due_from) params.set("due_from", filters.due_from);
  if (filters.due_to) params.set("due_to", filters.due_to);
  if (filters.sort) params.set("sort", filters.sort);
  return params;
}

/**
 * The Task List module (Doc 14 §10) — six saved presets over the single list endpoint, plus search,
 * filters, sorting, cursor pagination and bulk actions. State is URL-persisted, matching
 * `ContactsList`.
 */
export function TaskList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<Task | null>(null);

  const me = useCurrentUser();
  const preset = searchParams.get("preset") ?? "today";
  const query = useMemo(
    () => readQuery(searchParams, me.data?.id),
    [searchParams, me.data?.id],
  );

  // The "me"-scoped presets cannot be requested until the identity resolves.
  const tasks = useTasks(query, !me.isLoading);
  const bulkUpdate = useBulkUpdateTasks();
  const bulkDelete = useBulkDeleteTasks();

  const rows = tasks.data?.data ?? [];
  const page = tasks.data?.page;
  const selected = [...selectedIds];

  function apply(next: TaskListQuery): void {
    setSearchParams(writeQuery(preset, next)); // drops the cursor → back to the first page
  }

  function choosePreset(key: string): void {
    setSelectedIds(new Set());
    setSearchParams(writeQuery(key, {}));
  }

  function goToCursor(cursor: string): void {
    const params = writeQuery(preset, query);
    params.set("cursor", cursor);
    setSearchParams(params);
  }

  function toggle(id: string): void {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll(): void {
    setSelectedIds((prev) => {
      const allSelected = rows.length > 0 && rows.every((task) => prev.has(task.id));
      const next = new Set(prev);
      for (const task of rows) {
        if (allSelected) next.delete(task.id);
        else next.add(task.id);
      }
      return next;
    });
  }

  const bulkError = bulkUpdate.error ?? bulkDelete.error;
  const bulkPending = bulkUpdate.isPending || bulkDelete.isPending;

  return (
    <>
      <nav aria-label="Task views" className="mb-4 flex flex-wrap gap-2">
        {TASK_PRESETS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            onClick={() => choosePreset(entry.key)}
            aria-current={preset === entry.key ? "page" : undefined}
            className={`rounded-md border px-3 py-1 text-sm ${
              preset === entry.key
                ? "border-accent text-accent"
                : "border-border text-text-secondary hover:bg-hover"
            }`}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      <div className="mb-4">
        <TaskFilters filters={query} onChange={apply} />
      </div>

      {selectedIds.size > 0 ? (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm">
          <span>{selectedIds.size} selected</span>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={bulkPending}
              onClick={() =>
                bulkUpdate.mutate(
                  { taskIds: selected, set: { status: "completed" } },
                  { onSuccess: () => setSelectedIds(new Set()) },
                )
              }
            >
              Complete
            </button>
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={bulkPending}
              onClick={() =>
                bulkUpdate.mutate(
                  { taskIds: selected, set: { status: "cancelled" } },
                  { onSuccess: () => setSelectedIds(new Set()) },
                )
              }
            >
              Cancel
            </button>
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={bulkPending}
              onClick={() =>
                bulkUpdate.mutate(
                  { taskIds: selected, set: { priority: "high" } },
                  { onSuccess: () => setSelectedIds(new Set()) },
                )
              }
            >
              Set high priority
            </button>
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={bulkPending}
              onClick={() =>
                bulkDelete.mutate(selected, { onSuccess: () => setSelectedIds(new Set()) })
              }
            >
              Delete
            </button>
            <button
              type="button"
              onClick={() => setSelectedIds(new Set())}
              className="text-accent hover:underline"
            >
              Clear
            </button>
          </div>
        </div>
      ) : null}

      {bulkError ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(bulkError)} />
        </div>
      ) : null}

      {tasks.isLoading || me.isLoading ? (
        <Spinner label="Loading tasks…" />
      ) : tasks.isError ? (
        <ErrorState message={apiErrorMessage(tasks.error)} onRetry={() => void tasks.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No tasks here"
          description="Nothing matches this view. Create a task from a customer profile."
        />
      ) : (
        <>
          <TaskTable
            tasks={rows}
            selectedIds={selectedIds}
            onToggle={toggle}
            onToggleAll={toggleAll}
            onEdit={setEditing}
          />
          <nav aria-label="Pagination" className="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              disabled={!page?.prev_cursor}
              onClick={() => {
                if (page?.prev_cursor) goToCursor(page.prev_cursor);
              }}
              className={BUTTON_CLASS}
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!page?.next_cursor}
              onClick={() => {
                if (page?.next_cursor) goToCursor(page.next_cursor);
              }}
              className={BUTTON_CLASS}
            >
              Next
            </button>
          </nav>
        </>
      )}

      {editing ? <TaskForm task={editing} onClose={() => setEditing(null)} /> : null}
    </>
  );
}
