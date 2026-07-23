import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { useTags } from "@/features/customer-profile/api";
import { apiErrorMessage, useConversations } from "@/features/inbox/api";
import { ConversationFilters } from "@/features/inbox/ConversationFilters";
import { ConversationList } from "@/features/inbox/ConversationList";
import { ConversationThread } from "@/features/inbox/ConversationThread";
import type { InboxFilters } from "@/features/inbox/types";

const PAGE_SIZE = 25;
const PAGER_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs hover:bg-hover disabled:opacity-50";

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

/**
 * The Shared Inbox (Doc 02 G1–G10). Two panes — the filtered conversation rail and the open
 * thread — with all state in the URL, so a conversation is linkable (the Tasks feature already
 * links here as `/inbox?conversation=<id>`).
 */
export function Inbox(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const cursor = searchParams.get("cursor");
  const selectedId = searchParams.get("conversation");

  const tags = useTags();
  const conversations = useConversations(filters, cursor, PAGE_SIZE);

  const rows = conversations.data?.data ?? [];
  const page = conversations.data?.page;

  function applyFilters(next: InboxFilters): void {
    setSearchParams(writeParams(next, selectedId)); // drops the cursor → first page
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

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <div className="flex w-full shrink-0 flex-col border-b border-border lg:w-80 lg:border-b-0 lg:border-r">
        <ConversationFilters
          filters={filters}
          onChange={applyFilters}
          tags={(tags.data ?? []).map((tag) => ({
            id: tag.id,
            name: tag.name,
            color: tag.color ?? null,
          }))}
        />

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversations.isLoading ? (
            <div className="p-3">
              <Spinner label="Loading conversations…" />
            </div>
          ) : conversations.isError ? (
            <div className="p-3">
              <ErrorState
                message={apiErrorMessage(conversations.error)}
                onRetry={() => void conversations.refetch()}
              />
            </div>
          ) : rows.length === 0 ? (
            <EmptyState title="No conversations" description="Nothing matches these filters." />
          ) : (
            <ConversationList
              conversations={rows}
              selectedId={selectedId}
              onSelect={select}
            />
          )}
        </div>

        <nav aria-label="Conversation pagination" className="flex justify-end gap-2 border-t border-border p-2">
          <button
            type="button"
            disabled={!page?.prev_cursor}
            onClick={() => {
              if (page?.prev_cursor) goToCursor(page.prev_cursor);
            }}
            className={PAGER_CLASS}
          >
            Previous
          </button>
          <button
            type="button"
            disabled={!page?.next_cursor}
            onClick={() => {
              if (page?.next_cursor) goToCursor(page.next_cursor);
            }}
            className={PAGER_CLASS}
          >
            Next
          </button>
        </nav>
      </div>

      <div className="min-h-0 min-w-0 flex-1">
        {selectedId ? (
          <ConversationThread
            key={selectedId}
            conversationId={selectedId}
            tags={(tags.data ?? []).map((tag) => ({
              id: tag.id,
              name: tag.name,
              color: tag.color ?? null,
            }))}
          />
        ) : (
          <div className="p-6">
            <EmptyState
              title="Select a conversation"
              description="Choose a conversation from the list to read and reply."
            />
          </div>
        )}
      </div>
    </div>
  );
}
