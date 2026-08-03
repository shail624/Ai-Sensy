import {
  BookmarkPlus,
  Inbox,
  MessageCircleQuestion,
  MessagesSquare,
  Radio,
  Search,
  SlidersHorizontal,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button, Field, Input, Select, TagChip } from "@/components/ui";
import { useAssignableUsers } from "@/features/inbox/api";
import type { SavedInboxView } from "@/features/inbox/preferences";
import type { InboxFilters, TagSummary } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";

interface Props {
  filters: InboxFilters;
  onChange: (next: InboxFilters) => void;
  tags: TagSummary[];
  savedViews: SavedInboxView[];
  onSaveView: (name: string) => void;
  onDeleteView: (id: string) => void;
  currentUserId?: string;
}

/** Simple triage first; the complete filter and saved-view toolkit remains one click away. */
export function ConversationFilters({
  filters,
  onChange,
  tags,
  savedViews,
  onSaveView,
  onDeleteView,
  currentUserId,
}: Props): JSX.Element {
  const users = useAssignableUsers();
  const [viewName, setViewName] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function focusSearch(event: KeyboardEvent): void {
      if (
        event.key !== "/" ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      event.preventDefault();
      searchRef.current?.focus();
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  const quickInboxes = [
    {
      label: "Requests",
      description: "Open and unassigned",
      icon: MessageCircleQuestion,
      next: { status: "open", assignee: "unassigned" } satisfies InboxFilters,
    },
    {
      label: "Active",
      description: "All open chats",
      icon: MessagesSquare,
      next: { status: "open" } satisfies InboxFilters,
    },
    ...(currentUserId
      ? [
          {
            label: "My chats",
            description: "Assigned to me",
            icon: UserRound,
            next: { assignee: currentUserId } satisfies InboxFilters,
          },
        ]
      : []),
  ];

  const isQuickInboxActive = (next: InboxFilters): boolean =>
    filters.status === next.status && filters.assignee === next.assignee && !filters.tag;

  const advancedFilterCount =
    Number(Boolean(filters.status)) + Number(Boolean(filters.assignee)) + Number(Boolean(filters.tag));
  const hasListFilter = advancedFilterCount > 0 || Boolean(filters.q);

  function applyQuickInbox(next: InboxFilters): void {
    onChange(filters.q ? { ...next, q: filters.q } : next);
  }

  return (
    <div className="space-y-3 border-b border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-text-primary">Live Chat</p>
          <p className="text-[11px] text-text-secondary">One shared team inbox</p>
        </div>
        <span
          title="Conversation list refreshes every 10 seconds"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-success-soft px-2 py-1 text-[11px] font-semibold text-success-on-soft"
        >
          <Radio aria-hidden className="h-3 w-3" /> Auto-refresh · 10s
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5" aria-label="Live Chat views">
        {quickInboxes.map((quickInbox) => {
          const active = isQuickInboxActive(quickInbox.next);
          const Icon = quickInbox.icon;
          return (
            <button
              key={quickInbox.label}
              type="button"
              aria-pressed={active}
              onClick={() => applyQuickInbox(quickInbox.next)}
              className={`group min-w-0 rounded-lg border px-2 py-2.5 text-left transition-[border-color,background-color,box-shadow] ${
                active
                  ? "border-accent bg-accent-soft shadow-sm"
                  : "border-border bg-surface hover:border-accent/40 hover:bg-hover"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <Icon
                  aria-hidden
                  className={`h-4 w-4 shrink-0 ${
                    active ? "text-accent" : "text-text-disabled group-hover:text-accent"
                  }`}
                />
                <span
                  className={`truncate text-xs font-semibold ${active ? "text-accent-on-soft" : "text-text-primary"}`}
                >
                  {quickInbox.label}
                </span>
              </span>
              <span className="mt-1 block truncate text-[10px] text-text-disabled">
                {quickInbox.description}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex gap-2">
        <Input
          ref={searchRef}
          id="inbox-search"
          type="search"
          value={filters.q ?? ""}
          onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
          placeholder="Search chats…"
          aria-label="Search conversations"
          leadingIcon={<Search aria-hidden className="h-4 w-4" />}
          trailingAction={
            filters.q ? (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => onChange({ ...filters, q: undefined })}
                className="rounded-md p-1.5 text-text-disabled hover:bg-hover hover:text-text-primary"
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </button>
            ) : null
          }
          containerClassName="min-w-0 flex-1"
        />
        <Button
          type="button"
          size="md"
          variant={filtersOpen || advancedFilterCount > 0 ? "subtle" : "secondary"}
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen((open) => !open)}
          leftIcon={<SlidersHorizontal aria-hidden className="h-4 w-4" />}
          className="shrink-0 px-3 text-xs"
        >
          Filters
          {advancedFilterCount > 0 ? (
            <span className="rounded-full bg-accent px-1.5 py-0.5 text-[10px] text-accent-fg">
              {advancedFilterCount}
            </span>
          ) : null}
        </Button>
      </div>

      {savedViews.length > 0 ? (
        <div aria-label="Saved inboxes" className="flex items-center gap-1 overflow-x-auto pb-0.5">
          <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-text-disabled">
            Saved
          </span>
          {savedViews.map((view) => (
            <span
              key={view.id}
              className="inline-flex shrink-0 items-center rounded-full border border-border bg-surface-2"
            >
              <button
                type="button"
                onClick={() => onChange(view.filters)}
                className="px-2.5 py-1 text-xs font-medium text-text-primary"
              >
                {view.name}
              </button>
              <button
                type="button"
                aria-label={`Delete ${view.name} view`}
                onClick={() => onDeleteView(view.id)}
                className="mr-1 rounded-full p-1 text-text-disabled hover:text-danger"
              >
                <Trash2 aria-hidden className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      {filtersOpen ? (
        <section
          aria-label="Advanced inbox filters"
          className="space-y-3 rounded-xl border border-border bg-surface-2 p-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Inbox aria-hidden className="h-4 w-4 text-accent" />
              <p className="text-xs font-bold text-text-primary">Advanced filters</p>
            </div>
            {hasListFilter ? (
              <button
                type="button"
                onClick={() => onChange({})}
                className="text-xs font-semibold text-accent-on-soft hover:underline"
              >
                Show all
              </button>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Field htmlFor="inbox-status" label="Status">
              <Select
                id="inbox-status"
                value={filters.status ?? ""}
                onChange={(event) =>
                  onChange({ ...filters, status: event.target.value || undefined })
                }
              >
                <option value="">All statuses</option>
                {CONVERSATION_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STATUS_LABELS[status]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field htmlFor="inbox-assignee" label="Assignee">
              <Select
                id="inbox-assignee"
                value={filters.assignee ?? ""}
                onChange={(event) =>
                  onChange({ ...filters, assignee: event.target.value || undefined })
                }
              >
                <option value="">Anyone</option>
                <option value="unassigned">Unassigned</option>
                {(users.data ?? []).map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {tags.length > 0 ? (
            <div>
              <p className="mb-1.5 text-xs font-medium text-text-secondary">Labels</p>
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
            <Input
              id="saved-view-name"
              value={viewName}
              onChange={(event) => setViewName(event.target.value)}
              placeholder="Save these filters"
              maxLength={40}
              aria-label="Saved inbox name"
              className="flex-1"
            />
            <Button
              type="submit"
              variant="secondary"
              disabled={!viewName.trim()}
              aria-label="Save current filters"
              leftIcon={<BookmarkPlus aria-hidden className="h-4 w-4" />}
              className="px-3"
            />
          </form>
        </section>
      ) : null}
    </div>
  );
}
