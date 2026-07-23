import { TagChip } from "@/components/ui";
import { useAssignableUsers } from "@/features/inbox/api";
import type { InboxFilters, TagSummary } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

interface Props {
  filters: InboxFilters;
  onChange: (next: InboxFilters) => void;
  tags: TagSummary[];
}

/** Search + status/assignee/tag filters over the inbox list (Doc 04 §18.1). */
export function ConversationFilters({ filters, onChange, tags }: Props): JSX.Element {
  const users = useAssignableUsers();

  return (
    <div className="space-y-2 border-b border-border p-3">
      <div>
        <label htmlFor="inbox-search" className="sr-only">
          Search conversations
        </label>
        <input
          id="inbox-search"
          type="search"
          value={filters.q ?? ""}
          onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
          placeholder="Search name or number…"
          className={FIELD_CLASS}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label htmlFor="inbox-status" className="text-xs font-medium text-text-secondary">
            Status
          </label>
          <select
            id="inbox-status"
            value={filters.status ?? ""}
            onChange={(event) => onChange({ ...filters, status: event.target.value || undefined })}
            className={FIELD_CLASS}
          >
            <option value="">All</option>
            {CONVERSATION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="inbox-assignee" className="text-xs font-medium text-text-secondary">
            Assignee
          </label>
          <select
            id="inbox-assignee"
            value={filters.assignee ?? ""}
            onChange={(event) =>
              onChange({ ...filters, assignee: event.target.value || undefined })
            }
            className={FIELD_CLASS}
          >
            <option value="">Anyone</option>
            <option value="unassigned">Unassigned</option>
            {(users.data ?? []).map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {tags.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => {
            const active = filters.tag === tag.id;
            return (
              <button
                key={tag.id}
                type="button"
                aria-pressed={active}
                onClick={() => onChange({ ...filters, tag: active ? undefined : tag.id })}
                className={`rounded-full ${active ? "ring-2 ring-focus" : ""}`}
              >
                <TagChip name={tag.name} color={tag.color} />
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
