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

import { TagChip } from "@/components/ui";
import { useAssignableUsers } from "@/features/inbox/api";
import type { SavedInboxView } from "@/features/inbox/preferences";
import type { InboxFilters, TagSummary } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";

const FIELD_CLASS =
  "min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none transition focus:border-accent focus:ring-2 focus:ring-focus/20";

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
      if (event.key !== "/" || event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
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
      ? [{
          label: "My chats",
          description: "Assigned to me",
          icon: UserRound,
          next: { assignee: currentUserId } satisfies InboxFilters,
        }]
      : []),
  ];

  const isQuickInboxActive = (next: InboxFilters): boolean =>
    filters.status === next.status && filters.assignee === next.assignee && !filters.tag;

  const advancedFilterCount = Number(Boolean(filters.status)) + Number(Boolean(filters.assignee)) + Number(Boolean(filters.tag));
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
        <span title="Conversation list refreshes every 10 seconds" className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-success-soft px-2 py-1 text-[11px] font-semibold text-success">
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
              className={`group min-w-0 rounded-xl border px-2 py-2.5 text-left transition ${active ? "border-accent bg-accent-soft shadow-sm" : "border-border bg-surface hover:border-accent/40 hover:bg-hover"}`}
            >
              <span className="flex items-center gap-1.5">
                <Icon aria-hidden className={`h-4 w-4 shrink-0 ${active ? "text-accent" : "text-text-disabled group-hover:text-accent"}`} />
                <span className={`truncate text-xs font-semibold ${active ? "text-accent" : "text-text-primary"}`}>{quickInbox.label}</span>
              </span>
              <span className="mt-1 block truncate text-[10px] text-text-disabled">{quickInbox.description}</span>
            </button>
          );
        })}
      </div>

      <div className="flex gap-2">
        <div className="relative min-w-0 flex-1">
          <label htmlFor="inbox-search" className="sr-only">Search conversations</label>
          <Search aria-hidden className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-text-disabled" />
          <input
            ref={searchRef}
            id="inbox-search"
            type="search"
            value={filters.q ?? ""}
            onChange={(event) => onChange({ ...filters, q: event.target.value || undefined })}
            placeholder="Search chats…"
            className={`${FIELD_CLASS} pl-9 pr-8`}
          />
          {filters.q ? (
            <button type="button" aria-label="Clear search" onClick={() => onChange({ ...filters, q: undefined })} className="absolute right-2 top-2 rounded-lg p-1.5 text-text-disabled hover:bg-hover hover:text-text-primary">
              <X aria-hidden className="h-3.5 w-3.5" />
            </button>
          ) : null}
        </div>
        <button
          type="button"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen((open) => !open)}
          className={`relative inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border px-3 text-xs font-semibold transition ${filtersOpen || advancedFilterCount > 0 ? "border-accent bg-accent-soft text-accent" : "border-border text-text-secondary hover:bg-hover"}`}
        >
          <SlidersHorizontal aria-hidden className="h-4 w-4" /> Filters
          {advancedFilterCount > 0 ? <span className="rounded-full bg-accent px-1.5 py-0.5 text-[10px] text-accent-fg">{advancedFilterCount}</span> : null}
        </button>
      </div>

      {savedViews.length > 0 ? (
        <div aria-label="Saved inboxes" className="flex items-center gap-1 overflow-x-auto pb-0.5">
          <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-text-disabled">Saved</span>
          {savedViews.map((view) => (
            <span key={view.id} className="inline-flex shrink-0 items-center rounded-full border border-border bg-surface-subtle">
              <button type="button" onClick={() => onChange(view.filters)} className="px-2.5 py-1 text-xs font-medium text-text-primary">{view.name}</button>
              <button type="button" aria-label={`Delete ${view.name} view`} onClick={() => onDeleteView(view.id)} className="mr-1 rounded-full p-1 text-text-disabled hover:text-danger">
                <Trash2 aria-hidden className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      {filtersOpen ? (
        <section aria-label="Advanced inbox filters" className="space-y-3 rounded-2xl border border-border bg-surface-subtle p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Inbox aria-hidden className="h-4 w-4 text-accent" />
              <p className="text-xs font-bold text-text-primary">Advanced filters</p>
            </div>
            {hasListFilter ? <button type="button" onClick={() => onChange({})} className="text-xs font-semibold text-accent hover:underline">Show all</button> : null}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="inbox-status" className="mb-1 block text-xs font-medium text-text-secondary">Status</label>
              <select id="inbox-status" value={filters.status ?? ""} onChange={(event) => onChange({ ...filters, status: event.target.value || undefined })} className={FIELD_CLASS}>
                <option value="">All statuses</option>
                {CONVERSATION_STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="inbox-assignee" className="mb-1 block text-xs font-medium text-text-secondary">Assignee</label>
              <select id="inbox-assignee" value={filters.assignee ?? ""} onChange={(event) => onChange({ ...filters, assignee: event.target.value || undefined })} className={FIELD_CLASS}>
                <option value="">Anyone</option>
                <option value="unassigned">Unassigned</option>
                {(users.data ?? []).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}
              </select>
            </div>
          </div>

          {tags.length > 0 ? (
            <div>
              <p className="mb-1.5 text-xs font-medium text-text-secondary">Labels</p>
              <div className="flex flex-wrap gap-1">
                {tags.map((tag) => {
                  const active = filters.tag === tag.id;
                  return <button key={tag.id} type="button" aria-pressed={active} onClick={() => onChange({ ...filters, tag: active ? undefined : tag.id })} className={`rounded-full ${active ? "ring-2 ring-focus" : ""}`}><TagChip name={tag.name} color={tag.color} /></button>;
                })}
              </div>
            </div>
          ) : null}

          <form className="flex gap-2" onSubmit={(event) => {
            event.preventDefault();
            const name = viewName.trim();
            if (!name) return;
            onSaveView(name);
            setViewName("");
          }}>
            <label htmlFor="saved-view-name" className="sr-only">Saved inbox name</label>
            <input id="saved-view-name" value={viewName} onChange={(event) => setViewName(event.target.value)} placeholder="Save these filters" maxLength={40} className={FIELD_CLASS} />
            <button type="submit" disabled={!viewName.trim()} className="rounded-xl border border-border p-2.5 text-text-secondary hover:bg-hover disabled:opacity-40" aria-label="Save current filters">
              <BookmarkPlus aria-hidden className="h-4 w-4" />
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}
