import { BookmarkPlus, Radio, Search, Trash2 } from "lucide-react";
import { useState } from "react";

import { TagChip } from "@/components/ui";
import { useAssignableUsers } from "@/features/inbox/api";
import type { SavedInboxView } from "@/features/inbox/preferences";
import type { InboxFilters, TagSummary } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

interface Props {
  filters: InboxFilters;
  onChange: (next: InboxFilters) => void;
  tags: TagSummary[];
  savedViews: SavedInboxView[];
  onSaveView: (name: string) => void;
  onDeleteView: (id: string) => void;
}

/** Search + status/assignee/tag filters over the inbox list (Doc 04 §18.1). */
export function ConversationFilters({
  filters,
  onChange,
  tags,
  savedViews,
  onSaveView,
  onDeleteView,
}: Props): JSX.Element {
  const users = useAssignableUsers();
  const [viewName, setViewName] = useState("");

  return (
    <div className="space-y-3 border-b border-border bg-surface p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-text-primary">Shared inbox</p>
          <p className="text-[11px] text-text-secondary">Team conversations</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-2 py-1 text-[11px] font-semibold text-success">
          <Radio aria-hidden className="h-3 w-3" /> Live · 10s
        </span>
      </div>

      <div className="relative">
        <label htmlFor="inbox-search" className="sr-only">
          Search conversations
        </label>
        <Search aria-hidden className="pointer-events-none absolute left-2.5 top-2 h-4 w-4 text-text-disabled" />
        <input
          id="inbox-search"
          type="search"
          value={filters.q ?? ""}
          onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
          placeholder="Search name or number…"
          className={`${FIELD_CLASS} pl-8`}
        />
      </div>

      {savedViews.length > 0 ? (
        <div aria-label="Saved inbox views" className="flex gap-1 overflow-x-auto pb-1">
          {savedViews.map((view) => (
            <span key={view.id} className="inline-flex shrink-0 items-center rounded-full border border-border bg-surface-subtle">
              <button type="button" onClick={() => onChange(view.filters)} className="px-2.5 py-1 text-xs font-medium text-text-primary">
                {view.name}
              </button>
              <button type="button" aria-label={`Delete ${view.name} view`} onClick={() => onDeleteView(view.id)} className="mr-1 rounded-full p-1 text-text-disabled hover:text-danger">
                <Trash2 aria-hidden className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

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

      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const name = viewName.trim();
          if (!name) return;
          onSaveView(name);
          setViewName("");
        }}
      >
        <label htmlFor="saved-view-name" className="sr-only">Saved view name</label>
        <input
          id="saved-view-name"
          value={viewName}
          onChange={(event) => setViewName(event.target.value)}
          placeholder="Name this view"
          maxLength={40}
          className={FIELD_CLASS}
        />
        <button type="submit" disabled={!viewName.trim()} className="rounded-md border border-border p-2 text-text-secondary hover:bg-hover disabled:opacity-40" aria-label="Save current filters">
          <BookmarkPlus aria-hidden className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
