import { Link } from "react-router-dom";

import { TaskActions } from "@/features/tasks/TaskActions";
import {
  TaskDue,
  TaskPriorityChip,
  TaskStatusChip,
  TaskTypeChip,
} from "@/features/tasks/TaskBadges";
import type { Task } from "@/features/tasks/types";

interface Props {
  tasks: Task[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
  onEdit: (task: Task) => void;
}

/**
 * The shared task table (Doc 14 §10). Rows compose the same badge and action components the work
 * queue uses, so a task renders and behaves identically on every surface.
 */
export function TaskTable({
  tasks,
  selectedIds,
  onToggle,
  onToggleAll,
  onEdit,
}: Props): JSX.Element {
  const allSelected = tasks.length > 0 && tasks.every((task) => selectedIds.has(task.id));

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="w-10 px-3 py-2">
              <input
                type="checkbox"
                aria-label="Select all tasks on this page"
                checked={allSelected}
                onChange={onToggleAll}
              />
            </th>
            <th scope="col" className="px-3 py-2">Task</th>
            <th scope="col" className="px-3 py-2">Customer</th>
            <th scope="col" className="px-3 py-2">Due</th>
            <th scope="col" className="px-3 py-2">Priority</th>
            <th scope="col" className="px-3 py-2">Status</th>
            <th scope="col" className="px-3 py-2">Assignee</th>
            <th scope="col" className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id} className="border-b border-border last:border-0 hover:bg-hover">
              <td className="px-3 py-2">
                <input
                  type="checkbox"
                  aria-label={`Select ${task.title}`}
                  checked={selectedIds.has(task.id)}
                  onChange={() => onToggle(task.id)}
                />
              </td>
              <td className="px-3 py-2">
                <button
                  type="button"
                  onClick={() => onEdit(task)}
                  className="text-left font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  {task.title}
                </button>
                <div className="mt-1">
                  <TaskTypeChip value={task.task_type} />
                </div>
              </td>
              <td className="px-3 py-2">
                <Link
                  to={`/contacts/${task.contact_id}`}
                  className="text-text-secondary hover:text-accent"
                >
                  {task.contact_name ?? "—"}
                </Link>
              </td>
              <td className="px-3 py-2">
                <TaskDue task={task} />
              </td>
              <td className="px-3 py-2">
                <TaskPriorityChip value={task.priority} />
              </td>
              <td className="px-3 py-2">
                <TaskStatusChip value={task.status} />
              </td>
              <td className="px-3 py-2 text-text-secondary">
                {task.assigned_agent_name ?? "—"}
              </td>
              <td className="px-3 py-2">
                <TaskActions task={task} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
