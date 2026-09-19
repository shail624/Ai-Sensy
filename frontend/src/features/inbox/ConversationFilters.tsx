import {
  BookmarkPlus,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Radio,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button, Field, Input, Select, TagChip } from "@/components/ui";
import { useAssignableUsers, useConversationCounts } from "@/features/inbox/api";
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
  showProfileLabel?: boolean;
  listCollapsed?: boolean;
  onToggleList?: () => void;
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
  showProfileLabel = true,
  listCollapsed = false,
  onToggleList,
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

  // Counted under the search alone — the only filter a chip carries across — so each badge equals
  // the number of rows its own click produces. While the read is in flight the badge is omitted
  // rather than shown as zero, which would read as an emptiness the inbox has not established.
  const counts = useConversationCounts(filters.q);

  const quickInboxes = [
    {
      label: "Active",
      description: "All open chats",
      count: counts.data?.active,
      next: { status: "open" } satisfies InboxFilters,
    },
    {
      label: "Requesting",
      description: "Open chats without an assigned agent",
      count: counts.data?.requesting,
      next: { status: "open", assignee: "unassigned" } satisfies InboxFilters,
    },
    ...(currentUserId
      ? [
          {
            label: "Intervened",
            description: "Chats currently assigned to me",
            count: counts.data?.intervened,
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
    <div className="flex shrink-0 flex-col border-b border-border bg-surface">
      <div className="sr-only">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-bold text-text-primary">Live Chat</h1>
          <p className="text-[11px] text-text-secondary">One shared team inbox</p>
        </div>
        <span
          title="Conversation list refreshes every 10 seconds"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-success-soft px-2 py-1 text-[11px] font-semibold text-success-on-soft"
        >
          <Radio aria-hidden className="h-3 w-3" /> Auto-refresh · 10s
        </span>
      </div>

      <div className="flex w-full max-w-xl items-center gap-2 p-3">
        <Input
          ref={searchRef}
          id="inbox-search"
          type="search"
          value={filters.q ?? ""}
          onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
          placeholder="Search name or mobile number"
          aria-label="Search conversations"
          trailingAction={
            filters.q ? (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => onChange({ ...filters, q: undefined })}
                className="rounded-full bg-accent p-1.5 text-accent-fg hover:opacity-90"
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                type="button"
                aria-label="Search conversations"
                onClick={() => searchRef.current?.focus()}
                className="rounded-full bg-accent p-1.5 text-accent-fg hover:opacity-90"
              >
                <Search aria-hidden className="h-3.5 w-3.5" />
              </button>
            )
          }
          containerClassName="min-w-0 flex-1"
        />
        <Button
          type="button"
          size="md"
          variant={filtersOpen || advancedFilterCount > 0 ? "subtle" : "secondary"}
          aria-expanded={filtersOpen}
          aria-controls="advanced-inbox-filters"
          onClick={() => setFiltersOpen((open) => !open)}
          aria-label="Filters"
          title="Filters"
          className="shrink-0 px-2.5"
        >
          <SlidersHorizontal aria-hidden className="h-4 w-4" />
          {advancedFilterCount > 0 ? (
            <span className="sr-only">
              {advancedFilterCount}
            </span>
          ) : null}
        </Button>
        {onToggleList ? (
          <button
            type="button"
            onClick={onToggleList}
            aria-label={listCollapsed ? "Expand conversation list" : "Collapse conversation list"}
            title={listCollapsed ? "Expand conversation list" : "Collapse conversation list"}
            className="hidden rounded-control p-2 text-text-secondary hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus lg:inline-flex"
          >
            {listCollapsed ? <ChevronRight aria-hidden className="h-4 w-4" /> : <ChevronLeft aria-hidden className="h-4 w-4" />}
          </button>
        ) : null}
      </div>

      <div className="flex items-stretch bg-[var(--color-nav-bg)] text-[var(--color-nav-text)]" aria-label="Live Chat views">
        <div className="flex min-w-0 flex-1 overflow-x-auto">
        {quickInboxes.map((quickInbox) => {
          const active = isQuickInboxActive(quickInbox.next);
          return (
            <button
              key={quickInbox.label}
              type="button"
              aria-pressed={active}
              title={quickInbox.description}
              onClick={() => applyQuickInbox(quickInbox.next)}
              className={`min-h-14 shrink-0 border-b-[3px] px-4 text-xs font-semibold uppercase tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus sm:min-w-36 ${
                active
                  ? "border-[var(--color-nav-text)] bg-[var(--color-nav-active-bg)]"
                  : "border-transparent text-[var(--color-nav-muted)] hover:bg-[var(--color-nav-hover)]"
              }`}
            >
              {quickInbox.label}
              {/* The count sits inside the label as `ACTIVE (0)` rather than in a separate pill,
                  matching the reference tab strip the owner supplied. The accessible name is
                  unchanged — a pill and a parenthesis read the same to a screen reader, and the
                  count tests assert on that name rather than on the decoration around it. */}
              {quickInbox.count === undefined ? null : (
                <span
                  aria-label={`${quickInbox.count} in ${quickInbox.label}`}
                  className="ml-1.5 font-semibold tabular-nums"
                >
                  ({quickInbox.count})
                </span>
              )}
            </button>
          );
        })}
        </div>
        {showProfileLabel ? <span className="hidden w-72 shrink-0 items-center justify-center text-sm font-semibold xl:flex">Chat Profile</span> : null}
      </div>

      {savedViews.length > 0 ? (
        <div aria-label="Saved inboxes" className="order-2 flex items-center gap-1 overflow-x-auto px-3 py-2">
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
          id="advanced-inbox-filters"
          aria-label="Advanced inbox filters"
          className="order-3 space-y-3 border-t border-border bg-surface-2 p-3"
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
                className="text-xs font-semibold text-accent hover:underline"
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
              containerClassName="min-w-0 flex-1"
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
