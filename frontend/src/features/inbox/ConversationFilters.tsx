import {
  BookmarkPlus,
  Inbox,
  ListFilter,
  Radio,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button, Field, Input, Modal, Select, TagChip } from "@/components/ui";
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
  // Filters apply live; Discard restores what was in force when the dialog opened.
  const [openedWith, setOpenedWith] = useState<InboxFilters>(filters);
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

  const activeIndex = quickInboxes.findIndex((quickInbox) => isQuickInboxActive(quickInbox.next));

  const advancedFilterCount =
    Number(Boolean(filters.status)) + Number(Boolean(filters.assignee)) + Number(Boolean(filters.tag));
  const hasListFilter = advancedFilterCount > 0 || Boolean(filters.q);

  function applyQuickInbox(next: InboxFilters): void {
    onChange(filters.q ? { ...next, q: filters.q } : next);
  }

  return (
    <div className="flex shrink-0 flex-col">
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

      <div className="flex h-[60px] items-center gap-2 bg-[#fdfffc] pl-4 pr-2 dark:bg-surface">
        <div className="flex h-[34px] min-w-0 flex-1 items-center rounded-lg bg-[#f0f0f0] pl-[15px] pr-1.5 dark:bg-surface-2">
          <input
            ref={searchRef}
            id="inbox-search"
            type="search"
            value={filters.q ?? ""}
            onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
            placeholder="Search name or mobile number"
            aria-label="Search conversations"
            className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary [&::-webkit-search-cancel-button]:hidden"
          />
          {filters.q ? (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => onChange({ ...filters, q: undefined })}
              className="flex h-6 w-6 items-center justify-center rounded-full text-black/50 hover:bg-black/5"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              aria-label="Search conversations"
              onClick={() => searchRef.current?.focus()}
              className="flex h-6 w-6 items-center justify-center rounded-full text-black/50 hover:bg-black/5 dark:text-text-secondary"
            >
              <Search aria-hidden className="h-4 w-4" />
            </button>
          )}
        </div>
        <button
          type="button"
          aria-expanded={filtersOpen}
          aria-controls="advanced-inbox-filters"
          onClick={() => {
            setOpenedWith(filters);
            setFiltersOpen((open) => !open);
          }}
          aria-label={advancedFilterCount > 0 ? `Filters, ${advancedFilterCount} active` : "Filters"}
          title="Filters"
          className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-black/55 transition-colors duration-150 hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-text-secondary"
        >
          <ListFilter aria-hidden className="h-6 w-6" />
          {advancedFilterCount > 0 ? (
            <span
              aria-hidden
              className="absolute right-2 top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-nav-bg)] px-1 text-[9px] font-bold text-white"
            >
              {advancedFilterCount > 9 ? "9+" : advancedFilterCount}
            </span>
          ) : null}
        </button>
      </div>

      <div className="relative flex h-[50px] items-stretch bg-[var(--color-nav-bg)] text-white" aria-label="Live Chat views">
        {quickInboxes.map((quickInbox) => {
          const active = isQuickInboxActive(quickInbox.next);
          return (
            <button
              key={quickInbox.label}
              type="button"
              aria-pressed={active}
              title={quickInbox.description}
              onClick={() => applyQuickInbox(quickInbox.next)}
              className={`min-w-0 flex-1 px-[3px] text-[11px] font-medium uppercase tracking-[0.03em] transition-opacity duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-white/70 ${active ? "opacity-100" : "opacity-70 hover:opacity-100"}`}
            >
              {quickInbox.label}
              {quickInbox.count === undefined ? null : (
                <span aria-label={`${quickInbox.count} in ${quickInbox.label}`} className="ml-1 tabular-nums">
                  ({quickInbox.count})
                </span>
              )}
            </button>
          );
        })}
        {activeIndex >= 0 ? (
          <span
            aria-hidden
            className="absolute bottom-0 h-[3px] bg-white transition-[left] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
            style={{ width: `${100 / quickInboxes.length}%`, left: `${(100 / quickInboxes.length) * activeIndex}%` }}
          />
        ) : null}
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
        <Modal title="Filters" onClose={() => setFiltersOpen(false)} panelClassName="!max-w-[860px] !rounded-md">
        <p className="mb-3 text-sm text-text-secondary">Refine the live chat list by adding one or more filters.</p>
        <section
          id="advanced-inbox-filters"
          aria-label="Advanced inbox filters"
          className="space-y-3"
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
        <div className="mt-4 flex justify-end gap-2 border-t border-border pt-3">
          <button type="button" onClick={() => { onChange(openedWith); setFiltersOpen(false); }} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary">
            Discard
          </button>
          <button type="button" onClick={() => setFiltersOpen(false)} className="h-9 rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white hover:bg-[#08393d]">
            Apply Filters
          </button>
        </div>
        </Modal>
      ) : null}
    </div>
  );
}
