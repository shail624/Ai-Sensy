import { MessagesSquare, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorState, Pagination, Select, Skeleton } from "@/components/ui";
import { useTags } from "@/features/customer-profile/api";
import {
  apiErrorMessage,
  useAssignableUsers,
  useBulkAddConversationTags,
  useBulkAssignConversations,
  useBulkSetConversationStatus,
  useConversations,
} from "@/features/inbox/api";
import { ChatQuickSwitcher } from "@/features/inbox/ChatQuickSwitcher";
import { ConversationFilters } from "@/features/inbox/ConversationFilters";
import { ConversationList } from "@/features/inbox/ConversationList";
import { ConversationThread } from "@/features/inbox/ConversationThread";
import { NewChatDialog } from "@/features/inbox/NewChatDialog";
import { useInboxPreferences } from "@/features/inbox/preferences";
import type { InboxChannel, InboxFilters } from "@/features/inbox/types";
import {
  CONVERSATION_STATUSES,
  STATUS_LABELS,
  type ConversationStatus,
} from "@/features/inbox/types";
import { useAuth, useHasPermission } from "@/lib/auth";

const PAGE_SIZE = 25;

function readFilters(params: URLSearchParams): InboxFilters {
  return {
    status: params.get("status") ?? undefined,
    assignee: params.get("assignee") ?? undefined,
    tag: params.get("tag") ?? undefined,
    q: params.get("q") ?? undefined,
    channel: readChannel(params.get("channel")),
    sale: params.get("sale") ?? undefined,
  };
}

function readChannel(value: string | null): InboxChannel | undefined {
  return value === "official" || value === "qr" ? value : undefined;
}

function writeParams(filters: InboxFilters, conversationId: string | null): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.assignee) params.set("assignee", filters.assignee);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.q) params.set("q", filters.q);
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.sale) params.set("sale", filters.sale);
  if (conversationId) params.set("conversation", conversationId);
  return params;
}

/** Shared inbox. Server state remains authoritative; view preferences are browser-local per user. */
export function Inbox(): JSX.Element {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selection, setSelection] = useState<string[]>([]);
  const [listCollapsed, setListCollapsed] = useState(false);
  const [newChatOpen, setNewChatOpen] = useState(false);
  const canSend = useHasPermission("messages:send");
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const cursor = searchParams.get("cursor");
  const selectedId = searchParams.get("conversation");

  // Like the reference, a bare visit to Live Chat lands on the Active tab (open chats), not on an
  // unfiltered list that no tab represents. Any explicit filter or deep link is left untouched.
  useEffect(() => {
    if ([...searchParams.keys()].length === 0) {
      setSearchParams(new URLSearchParams({ status: "open" }), { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const tags = useTags();
  const conversations = useConversations(filters, cursor, PAGE_SIZE);
  const preferences = useInboxPreferences(user?.id);
  const assignees = useAssignableUsers();
  const bulkStatus = useBulkSetConversationStatus();
  const bulkAssign = useBulkAssignConversations();
  const bulkTags = useBulkAddConversationTags();
  const rows = conversations.data?.data ?? [];
  const page = conversations.data?.page;
  const tagOptions = (tags.data ?? []).map((tag) => ({
    id: tag.id,
    name: tag.name,
    color: tag.color ?? null,
  }));
  const bulkPending = bulkStatus.isPending || bulkAssign.isPending || bulkTags.isPending;
  const bulkError = bulkStatus.error ?? bulkAssign.error ?? bulkTags.error;

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
    setSelection((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  return (
    <div className="flex h-full min-h-0 bg-canvas">
      <div
        className={`${selectedId ? "hidden lg:flex" : "flex"} ${listCollapsed ? "lg:hidden" : ""} min-h-0 w-full flex-col bg-[#fdfbf7] dark:bg-surface lg:w-[380px] lg:flex-none lg:border-r lg:border-[#f2f2f2] dark:lg:border-border`}
      >
        <ConversationFilters
          filters={filters}
          onChange={applyFilters}
          tags={tagOptions}
          savedViews={preferences.savedViews}
          onSaveView={(name) => preferences.saveView(name, filters)}
          onDeleteView={preferences.deleteView}
          currentUserId={user?.id}
          onNewChat={canSend ? () => setNewChatOpen(true) : undefined}
        />

        {selection.length > 0 ? (
          <div className="border-b border-border bg-accent-soft p-3" aria-label="Bulk actions">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-bold text-accent-on-soft">
                {selection.length} selected
              </span>
              <button
                type="button"
                onClick={() => setSelection([])}
                aria-label="Clear selection"
                className="rounded-md p-1 text-text-secondary hover:bg-hover"
              >
                <X aria-hidden className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-1">
              <Select
                id="bulk-status"
                aria-label="Change status for selected conversations"
                defaultValue=""
                disabled={bulkPending}
                controlSize="sm"
                onChange={(event) => {
                  if (!event.target.value) return;
                  void bulkStatus
                    .mutateAsync({
                      ids: selection,
                      status: event.target.value as ConversationStatus,
                    })
                    .then(() => setSelection([]));
                }}
              >
                <option value="">Change status…</option>
                {CONVERSATION_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STATUS_LABELS[status]}
                  </option>
                ))}
              </Select>
              <Select
                id="bulk-assignee"
                aria-label="Assign selected conversations"
                defaultValue=""
                disabled={bulkPending}
                controlSize="sm"
                onChange={(event) => {
                  if (!event.target.value) return;
                  void bulkAssign
                    .mutateAsync({ ids: selection, assigneeId: event.target.value })
                    .then(() => setSelection([]));
                }}
              >
                <option value="">Assign…</option>
                {(assignees.data ?? []).map((assignee) => (
                  <option key={assignee.id} value={assignee.id}>
                    {assignee.full_name}
                  </option>
                ))}
              </Select>
              <Select
                id="bulk-tag"
                aria-label="Label selected conversations"
                defaultValue=""
                disabled={bulkPending}
                controlSize="sm"
                onChange={(event) => {
                  if (!event.target.value) return;
                  void bulkTags
                    .mutateAsync({ ids: selection, tagId: event.target.value })
                    .then(() => setSelection([]));
                }}
              >
                <option value="">Add label…</option>
                {tagOptions.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </Select>
            </div>
            {bulkError ? (
              <p role="alert" className="mt-2 text-xs text-danger-on-soft">
                {apiErrorMessage(bulkError)}
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversations.isLoading ? (
            <div className="space-y-3 p-3" aria-label="Loading conversations">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-20 w-full rounded-xl" />
              ))}
            </div>
          ) : conversations.isError ? (
            <div className="p-3">
              <ErrorState
                message={apiErrorMessage(conversations.error)}
                onRetry={() => void conversations.refetch()}
              />
            </div>
          ) : rows.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-7 px-6 text-center">
              <MessagesSquare aria-hidden className="h-24 w-24 text-[#0a474c]/15" strokeWidth={1.25} />
              <div>
                <p className="text-sm text-black dark:text-text-primary">Seems clear !</p>
                {filters.q || filters.tag ? (
                  <p className="mt-1 text-xs text-[#808080]">No chat matches these filters. Try clearing a filter or your search.</p>
                ) : null}
              </div>
            </div>
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

        {page?.prev_cursor || page?.next_cursor ? (
        <Pagination
          compact
          label="Conversation pagination"
          hasPrevious={Boolean(page?.prev_cursor)}
          hasNext={Boolean(page?.next_cursor)}
          busy={conversations.isFetching}
          onPrevious={() => {
            if (page?.prev_cursor) goToCursor(page.prev_cursor);
          }}
          onNext={() => {
            if (page?.next_cursor) goToCursor(page.next_cursor);
          }}
        />
        ) : null}
      </div>

      <div className={`${selectedId ? "flex" : "hidden lg:flex"} min-h-0 min-w-0 flex-1 flex-col`}>
        <ChatQuickSwitcher
          conversations={rows}
          selectedId={selectedId}
          onSelect={select}
          listCollapsed={listCollapsed}
          onToggleList={() => setListCollapsed((collapsed) => !collapsed)}
        />
        {selectedId ? (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1">
              <ConversationThread
                key={selectedId}
                conversationId={selectedId}
                onBack={() => setSearchParams(writeParams(filters, null))}
                tags={tagOptions}
                pinned={preferences.pinned.includes(selectedId)}
                onTogglePinned={() => preferences.togglePinned(selectedId)}
              />
            </div>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1">
            <div className="flex min-w-0 flex-1 flex-col">
              <div aria-hidden className="h-[50px] shrink-0 bg-[var(--color-nav-bg)]" />
              <div className="chat-wallpaper flex min-h-0 flex-1 items-center justify-center p-6">
                <p className="text-center text-base text-black dark:text-text-primary">Select a chat to continue!</p>
              </div>
            </div>
            <aside aria-label="Chat profile" className="hidden w-[340px] shrink-0 flex-col bg-[#f8f8f8] dark:bg-surface xl:flex">
              <h2 className="flex h-[50px] shrink-0 items-center justify-center bg-[var(--color-nav-bg)] text-base font-normal text-white">Chat Profile</h2>
              <div className="flex flex-col items-center gap-3 p-6 text-center">
                <span className="flex h-[55px] w-[55px] items-center justify-center rounded-full bg-[#ffa500] text-white">
                  <UserRound aria-hidden className="h-9 w-9" />
                </span>
                <p className="text-sm text-text-secondary">Select a chat to view the customer profile.</p>
              </div>
            </aside>
          </div>
        )}
      </div>
      {newChatOpen ? (
        <NewChatDialog onClose={() => setNewChatOpen(false)} onStarted={(id) => select(id)} />
      ) : null}
    </div>
  );
}
