import { ArrowLeft, CheckCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useTags } from "@/features/customer-profile/api";
import {
  apiErrorMessage,
  useAssignableUsers,
  useBulkAssignConversations,
  useBulkSetConversationStatus,
  useConversations,
} from "@/features/inbox/api";
import { ConversationFilters } from "@/features/inbox/ConversationFilters";
import { ConversationList } from "@/features/inbox/ConversationList";
import { ConversationThread } from "@/features/inbox/ConversationThread";
import { useInboxPreferences } from "@/features/inbox/preferences";
import type { InboxFilters } from "@/features/inbox/types";
import { useAuth } from "@/lib/auth";

const PAGE_SIZE = 25;
const PAGER_CLASS = "rounded-md border border-border px-2 py-1 text-xs hover:bg-hover disabled:opacity-50";

function readFilters(params: URLSearchParams): InboxFilters {
  return {
    status: params.get("status") ?? undefined,
    assignee: params.get("assignee") ?? undefined,
    tag: params.get("tag") ?? undefined,
    q: params.get("q") ?? undefined,
  };
}

function writeParams(filters: InboxFilters, conversationId: string | null): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.assignee) params.set("assignee", filters.assignee);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.q) params.set("q", filters.q);
  if (conversationId) params.set("conversation", conversationId);
  return params;
}

/** Shared inbox. Server state remains authoritative; view preferences are browser-local per user. */
export function Inbox(): JSX.Element {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selection, setSelection] = useState<string[]>([]);
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const cursor = searchParams.get("cursor");
  const selectedId = searchParams.get("conversation");

  const tags = useTags();
  const conversations = useConversations(filters, cursor, PAGE_SIZE);
  const preferences = useInboxPreferences(user?.id);
  const assignees = useAssignableUsers();
  const bulkStatus = useBulkSetConversationStatus();
  const bulkAssign = useBulkAssignConversations();
  const rows = conversations.data?.data ?? [];
  const page = conversations.data?.page;
  const tagOptions = (tags.data ?? []).map((tag) => ({ id: tag.id, name: tag.name, color: tag.color ?? null }));
  const bulkPending = bulkStatus.isPending || bulkAssign.isPending;
  const bulkError = bulkStatus.error ?? bulkAssign.error;

  function applyFilters(next: InboxFilters): void {
    setSearchParams(writeParams(next, selectedId));
  }

  function select(conversationId: string): void {
    const params = writeParams(filters, conversationId);
    if (cursor) params.set("cursor", cursor);
    setSearchParams(params);
  }

  function goToCursor(next: string): void {
    const params = writeParams(filters, selectedId);
    params.set("cursor", next);
    setSearchParams(params);
  }

  function toggleSelection(id: string): void {
    setSelection((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-canvas lg:flex-row">
      <div className={`${selectedId ? "hidden lg:flex" : "flex"} w-full shrink-0 flex-col border-b border-border bg-surface lg:w-[360px] lg:border-b-0 lg:border-r`}>
        <ConversationFilters
          filters={filters}
          onChange={applyFilters}
          tags={tagOptions}
          savedViews={preferences.savedViews}
          onSaveView={(name) => preferences.saveView(name, filters)}
          onDeleteView={preferences.deleteView}
        />

        {selection.length > 0 ? (
          <div className="border-b border-border bg-accent-soft p-3" aria-label="Bulk actions">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-bold text-accent">{selection.length} selected</span>
              <button type="button" onClick={() => setSelection([])} aria-label="Clear selection" className="rounded p-1 text-text-secondary hover:bg-hover">
                <X aria-hidden className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={bulkPending}
                onClick={() => void bulkStatus.mutateAsync({ ids: selection, status: "resolved" }).then(() => setSelection([]))}
                className="inline-flex items-center justify-center gap-1.5 rounded-md bg-accent px-2 py-2 text-xs font-semibold text-accent-fg disabled:opacity-50"
              >
                <CheckCheck aria-hidden className="h-3.5 w-3.5" /> Resolve
              </button>
              <label className="sr-only" htmlFor="bulk-assignee">Assign selected conversations</label>
              <select
                id="bulk-assignee"
                aria-label="Assign selected conversations"
                defaultValue=""
                disabled={bulkPending}
                onChange={(event) => {
                  if (!event.target.value) return;
                  void bulkAssign.mutateAsync({ ids: selection, assigneeId: event.target.value }).then(() => setSelection([]));
                }}
                className="rounded-md border border-border bg-surface px-2 py-2 text-xs text-text-primary"
              >
                <option value="">Assign…</option>
                {(assignees.data ?? []).map((assignee) => <option key={assignee.id} value={assignee.id}>{assignee.full_name}</option>)}
              </select>
            </div>
            {bulkError ? <p role="alert" className="mt-2 text-xs text-danger">{apiErrorMessage(bulkError)}</p> : null}
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversations.isLoading ? (
            <div className="space-y-3 p-3" aria-label="Loading conversations">
              {Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-20 w-full rounded-xl" />)}
            </div>
          ) : conversations.isError ? (
            <div className="p-3"><ErrorState message={apiErrorMessage(conversations.error)} onRetry={() => void conversations.refetch()} /></div>
          ) : rows.length === 0 ? (
            <EmptyState title="No conversations" description="Nothing matches these filters. Try clearing a filter or changing your search." />
          ) : (
            <ConversationList
              conversations={rows}
              selectedId={selectedId}
              onSelect={select}
              pinnedIds={preferences.pinned}
              onTogglePinned={preferences.togglePinned}
              selection={selection}
              onToggleSelection={toggleSelection}
            />
          )}
        </div>

        <nav aria-label="Conversation pagination" className="flex justify-end gap-2 border-t border-border p-2">
          <button type="button" disabled={!page?.prev_cursor} onClick={() => page?.prev_cursor && goToCursor(page.prev_cursor)} className={PAGER_CLASS}>Previous</button>
          <button type="button" disabled={!page?.next_cursor} onClick={() => page?.next_cursor && goToCursor(page.next_cursor)} className={PAGER_CLASS}>Next</button>
        </nav>
      </div>

      <div className={`${selectedId ? "block" : "hidden lg:block"} min-h-0 min-w-0 flex-1`}>
        {selectedId ? (
          <div className="flex h-full min-h-0 flex-col">
            <button type="button" onClick={() => setSearchParams(writeParams(filters, null))} className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3 text-sm font-semibold text-text-primary lg:hidden">
              <ArrowLeft aria-hidden className="h-4 w-4" /> Back to conversations
            </button>
            <div className="min-h-0 flex-1">
              <ConversationThread key={selectedId} conversationId={selectedId} tags={tagOptions} />
            </div>
          </div>
        ) : (
          <div className="p-6"><EmptyState title="Select a conversation" description="Choose a conversation to read, collaborate, and reply." /></div>
        )}
      </div>
    </div>
  );
}
