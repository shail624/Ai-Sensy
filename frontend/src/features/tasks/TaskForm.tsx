import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useCreateTask, useUpdateTask } from "@/features/tasks/api";
import type { Task, TaskPriority, TaskType } from "@/features/tasks/types";
import {
  TASK_PRIORITIES,
  TASK_PRIORITY_LABELS,
  TASK_TYPE_LABELS,
  TASK_TYPES,
} from "@/features/tasks/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

// Mirrors the server's constraints (title ≤160, description ≤4096, Doc 14 §5.1) so the user gets
// immediate feedback; the API remains the authority and its 422 is surfaced verbatim.
const schema = z.object({
  title: z.string().trim().min(1, "Title is required").max(160, "Title is too long"),
  task_type: z.enum(TASK_TYPES as [TaskType, ...TaskType[]]),
  priority: z.enum(TASK_PRIORITIES as [TaskPriority, ...TaskPriority[]]),
  due_at: z.string().min(1, "Due date is required"),
  has_time: z.boolean(),
  reminder_at: z.string(),
  description: z.string().max(4096, "Description is too long"),
});

type FormValues = z.infer<typeof schema>;

/** `datetime-local` works in local time; the API takes ISO instants. */
function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function toIso(local: string): string {
  return new Date(local).toISOString();
}

function defaultDue(): string {
  const tomorrow = new Date(Date.now() + 86_400_000);
  tomorrow.setHours(9, 0, 0, 0);
  return toLocalInput(tomorrow.toISOString());
}

interface Props {
  /** Required when creating; ignored when editing (a task's contact never moves). */
  contactId?: string;
  /** Present → edit that task; absent → create a new one. */
  task?: Task;
  onClose: () => void;
}

/**
 * Create/edit dialog (Doc 14 §15). Create posts the whole task; edit sends a PATCH carrying
 * `expected_row_version`, so a concurrent change surfaces as the server's 409 rather than
 * silently overwriting (TA-INV 7).
 */
export function TaskForm({ contactId, task, onClose }: Props): JSX.Element {
  const create = useCreateTask();
  const update = useUpdateTask();
  const editing = task !== undefined;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: task?.title ?? "",
      task_type: (task?.task_type as TaskType) ?? "call",
      priority: (task?.priority as TaskPriority) ?? "medium",
      due_at: task ? toLocalInput(task.due_at) : defaultDue(),
      has_time: task?.has_time ?? true,
      reminder_at: toLocalInput(task?.reminder_at ?? null),
      description: task?.description ?? "",
    },
  });

  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const onSubmit = handleSubmit((values) => {
    const shared = {
      title: values.title.trim(),
      task_type: values.task_type,
      priority: values.priority,
      due_at: toIso(values.due_at),
      has_time: values.has_time,
      reminder_at: values.reminder_at ? toIso(values.reminder_at) : null,
      description: values.description.trim() || null,
    };

    if (editing) {
      update.mutate(
        { taskId: task.id, body: { ...shared, expected_row_version: task.row_version } },
        { onSuccess: onClose },
      );
      return;
    }
    if (!contactId) return;
    create.mutate({ ...shared, contact_id: contactId }, { onSuccess: onClose });
  });

  return (
    <Modal title={editing ? "Edit task" : "New task"} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label htmlFor="task-title" className="text-xs font-medium text-text-secondary">
            Title
          </label>
          <input id="task-title" {...register("title")} className={FIELD_CLASS} />
          {errors.title ? <p className="text-xs text-danger">{errors.title.message}</p> : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="task-type" className="text-xs font-medium text-text-secondary">
              Type
            </label>
            <select id="task-type" {...register("task_type")} className={FIELD_CLASS}>
              {TASK_TYPES.map((type) => (
                <option key={type} value={type}>
                  {TASK_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="task-priority" className="text-xs font-medium text-text-secondary">
              Priority
            </label>
            <select id="task-priority" {...register("priority")} className={FIELD_CLASS}>
              {TASK_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {TASK_PRIORITY_LABELS[priority]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="task-due" className="text-xs font-medium text-text-secondary">
              Due
            </label>
            <input
              id="task-due"
              type="datetime-local"
              {...register("due_at")}
              className={FIELD_CLASS}
            />
            {errors.due_at ? <p className="text-xs text-danger">{errors.due_at.message}</p> : null}
          </div>
          <div>
            <label htmlFor="task-reminder" className="text-xs font-medium text-text-secondary">
              Reminder (optional)
            </label>
            <input
              id="task-reminder"
              type="datetime-local"
              {...register("reminder_at")}
              className={FIELD_CLASS}
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-xs text-text-secondary">
          <input type="checkbox" {...register("has_time")} />
          Task has a specific time (uncheck for an all-day task)
        </label>

        <div>
          <label htmlFor="task-description" className="text-xs font-medium text-text-secondary">
            Description
          </label>
          <textarea
            id="task-description"
            rows={3}
            {...register("description")}
            className={FIELD_CLASS}
          />
          {errors.description ? (
            <p className="text-xs text-danger">{errors.description.message}</p>
          ) : null}
        </div>

        {error ? <p className="text-sm text-danger">{apiErrorMessage(error)}</p> : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {editing ? "Save changes" : "Create task"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
