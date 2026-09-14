import type {
  TaskListQuery,
  TaskPriority,
  TaskSort,
  TaskStatus,
  TaskType,
} from "@/features/tasks/types";
import {
  TASK_PRIORITIES,
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
  TASK_STATUSES,
  TASK_TYPE_LABELS,
  TASK_TYPES,
} from "@/features/tasks/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORT_OPTIONS: { value: TaskSort; label: string }[] = [
  { value: "due_at", label: "Due date (soonest)" },
  { value: "-due_at", label: "Due date (latest)" },
  { value: "-priority", label: "Priority (highest)" },
  { value: "priority", label: "Priority (lowest)" },
  { value: "-created_at", label: "Newest" },
  { value: "created_at", label: "Oldest" },
  { value: "-completed_at", label: "Recently completed" },
];

interface Props {
  filters: TaskListQuery;
  onChange: (next: TaskListQuery) => void;
}

/** Search, status/type/priority, due window and sort — the §7.2 filter grammar, one control each. */
export function TaskFilters({ filters, onChange }: Props): JSX.Element {
  function setSingle<K extends keyof TaskListQuery>(key: K, value: TaskListQuery[K]): void {
    onChange({ ...filters, [key]: value });
  }

  /** The repeatable enum filters accept many values; this toolbar exposes one at a time. */
  function setEnumList<K extends "status" | "type" | "priority">(key: K, value: string): void {
    onChange({ ...filters, [key]: value ? ([value] as TaskListQuery[K]) : null });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-search" className="text-xs font-medium text-text-secondary">
          Search
        </label>
        <input
          id="tasks-search"
          type="search"
          value={filters.q ?? ""}
          onChange={(event) => setSingle("q", event.target.value || null)}
          placeholder="Title or description…"
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-status" className="text-xs font-medium text-text-secondary">
          Status
        </label>
        <select
          id="tasks-status"
          value={filters.status?.[0] ?? ""}
          onChange={(event) => setEnumList("status", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All statuses</option>
          {TASK_STATUSES.map((status: TaskStatus) => (
            <option key={status} value={status}>
              {TASK_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-type" className="text-xs font-medium text-text-secondary">
          Type
        </label>
        <select
          id="tasks-type"
          value={filters.type?.[0] ?? ""}
          onChange={(event) => setEnumList("type", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All types</option>
          {TASK_TYPES.map((type: TaskType) => (
            <option key={type} value={type}>
              {TASK_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-priority" className="text-xs font-medium text-text-secondary">
          Priority
        </label>
        <select
          id="tasks-priority"
          value={filters.priority?.[0] ?? ""}
          onChange={(event) => setEnumList("priority", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All priorities</option>
          {TASK_PRIORITIES.map((priority: TaskPriority) => (
            <option key={priority} value={priority}>
              {TASK_PRIORITY_LABELS[priority]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-due-from" className="text-xs font-medium text-text-secondary">
          Due from
        </label>
        <input
          id="tasks-due-from"
          type="date"
          value={filters.due_from?.slice(0, 10) ?? ""}
          onChange={(event) =>
            setSingle("due_from", event.target.value ? `${event.target.value}T00:00:00Z` : null)
          }
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-due-to" className="text-xs font-medium text-text-secondary">
          Due to
        </label>
        <input
          id="tasks-due-to"
          type="date"
          value={filters.due_to?.slice(0, 10) ?? ""}
          onChange={(event) =>
            setSingle("due_to", event.target.value ? `${event.target.value}T23:59:59Z` : null)
          }
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="tasks-sort" className="text-xs font-medium text-text-secondary">
          Sort
        </label>
        <select
          id="tasks-sort"
          value={filters.sort ?? "due_at"}
          onChange={(event) => setSingle("sort", event.target.value as TaskSort)}
          className={FIELD_CLASS}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
