import { ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useCurrentUser, useTaskStats, useTasks } from "@/features/tasks/api";
import { TaskActions } from "@/features/tasks/TaskActions";
import { TaskDue, TaskPriorityChip, TaskTypeChip } from "@/features/tasks/TaskBadges";
import type { Task, TaskListQuery } from "@/features/tasks/types";

const BUCKET_SIZE = 5;

interface BucketProps {
  label: string;
  count?: number;
  query: TaskListQuery;
  enabled: boolean;
}

function Bucket({ label, count, query, enabled }: BucketProps): JSX.Element {
  const tasks = useTasks({ ...query, limit: BUCKET_SIZE }, enabled);
  const rows: Task[] = tasks.data?.data ?? [];

  return (
    <Section
      title={label}
      action={
        count !== undefined ? (
          <span className="rounded-full border border-border px-2 py-0.5 text-xs text-text-secondary">
            {count}
          </span>
        ) : null
      }
    >
      {tasks.isLoading ? (
        <Spinner label={`Loading ${label.toLowerCase()}…`} />
      ) : tasks.isError ? (
        <ErrorState message={apiErrorMessage(tasks.error)} onRetry={() => void tasks.refetch()} />
      ) : rows.length === 0 ? (
        <p className="py-1 text-center text-sm text-text-secondary">Nothing here</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((task) => (
            <li
              key={task.id}
              className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-border px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{task.title}</p>
                <p className="mt-1 text-xs text-text-secondary">{task.contact_name ?? "—"}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1 text-xs">
                  <TaskTypeChip value={task.task_type} />
                  <TaskPriorityChip value={task.priority} />
                  <TaskDue task={task} />
                </div>
              </div>
              <TaskActions task={task} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

/**
 * My Work Queue (Doc 14 §11) — Overdue · Due Today · Upcoming · Completed Today for the signed-in
 * agent. Header counts come from the single `/tasks/stats` call so badges render before the lists
 * resolve; rows reuse the shared badge and action components, so a task behaves the same here as in
 * the task list. Reusable: embeddable on the dashboard or any future surface.
 */
export function MyWorkQueue(): JSX.Element {
  const me = useCurrentUser();
  const stats = useTaskStats();
  const meId = me.data?.id;
  const enabled = Boolean(meId);
  const scoped = (query: TaskListQuery): TaskListQuery => ({ ...query, assignee_id: meId });

  if (me.isError) {
    return <ErrorState message={apiErrorMessage(me.error)} onRetry={() => void me.refetch()} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Bucket
        label="Overdue"
        count={stats.data?.overdue}
        query={scoped({ view: "overdue" })}
        enabled={enabled}
      />
      <Bucket
        label="Due Today"
        count={stats.data?.due_today}
        query={scoped({ view: "today" })}
        enabled={enabled}
      />
      <Bucket
        label="Upcoming"
        count={stats.data?.upcoming}
        query={scoped({ view: "upcoming" })}
        enabled={enabled}
      />
      <Bucket
        label="Completed Today"
        count={stats.data?.completed_today}
        query={scoped({ status: ["completed"], sort: "-completed_at" })}
        enabled={enabled}
      />
    </div>
  );
}
