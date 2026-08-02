import { useState } from "react";
import { Link } from "react-router-dom";

import {
  apiErrorMessage,
  useCompleteTask,
  useReopenTask,
  useRescheduleTask,
  useSnoozeTask,
} from "@/features/tasks/api";
import type { Task } from "@/features/tasks/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

/** `datetime-local` wants `YYYY-MM-DDTHH:mm` in local time; the API wants ISO/UTC. */
function toLocalInput(iso: string): string {
  const date = new Date(iso);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

interface Props {
  task: Task;
  /** Hides the navigation links where the surrounding surface already provides them. */
  showLinks?: boolean;
}

/**
 * The per-task inline actions of FR-TASK-11 — Complete, Reschedule, Open customer, Open
 * conversation. One implementation, used identically by the task table and the work queue so a task
 * behaves the same everywhere (Doc 14 §10). Mutations invalidate the feature's queries.
 */
export function TaskActions({ task, showLinks = true }: Props): JSX.Element {
  const [rescheduling, setRescheduling] = useState(false);
  const [dueAt, setDueAt] = useState(() => toLocalInput(task.due_at));
  const complete = useCompleteTask();
  const reopen = useReopenTask();
  const reschedule = useRescheduleTask();
  const snooze = useSnoozeTask();

  const pending = complete.isPending || reopen.isPending || reschedule.isPending || snooze.isPending;
  const error = complete.error ?? reopen.error ?? reschedule.error ?? snooze.error;
  const isOpen = task.status === "open";

  function submitReschedule(): void {
    reschedule.mutate(
      { taskId: task.id, dueAt: new Date(dueAt).toISOString(), hasTime: task.has_time, expectedRowVersion: task.row_version },
      { onSuccess: () => setRescheduling(false) },
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {isOpen ? (
          <>
            <button
              type="button"
              className={ACTION_CLASS}
              disabled={pending}
              onClick={() => complete.mutate({ taskId: task.id, expectedRowVersion: task.row_version })}
            >
              Complete
            </button>
            <button
              type="button"
              className={ACTION_CLASS}
              disabled={pending}
              onClick={() => setRescheduling((open) => !open)}
              aria-expanded={rescheduling}
            >
              Reschedule
            </button>
            <button
              type="button"
              className={ACTION_CLASS}
              disabled={pending}
              onClick={() => snooze.mutate({ taskId: task.id, minutes: 60, expectedRowVersion: task.row_version })}
            >
              Snooze 1h
            </button>
          </>
        ) : (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => reopen.mutate(task.id)}
          >
            Reopen
          </button>
        )}

        {showLinks ? (
          <>
            <Link to={`/contacts/${task.contact_id}`} className={ACTION_CLASS}>
              Customer
            </Link>
            {task.conversation_id ? (
              <Link to={`/inbox?conversation=${task.conversation_id}`} className={ACTION_CLASS}>
                Conversation
              </Link>
            ) : null}
          </>
        ) : null}
      </div>

      {rescheduling ? (
        <div className="flex items-center gap-1">
          <label className="sr-only" htmlFor={`due-${task.id}`}>
            New due date for {task.title}
          </label>
          <input
            id={`due-${task.id}`}
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
            className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
          />
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending || !dueAt}
            onClick={submitReschedule}
          >
            Save
          </button>
        </div>
      ) : null}

      {error ? <p className="text-xs text-danger">{apiErrorMessage(error)}</p> : null}
    </div>
  );
}
