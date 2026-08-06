import { ArrowLeft, ExternalLink, History, Search, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Pagination,
  Select,
  Spinner,
  TagChip,
} from "@/components/ui";
import { usePhoneNumbers } from "@/features/campaigns/api";
import {
  apiErrorMessage,
  useAssignableUsers,
  useConversation,
  useConversations,
  useMessages,
} from "@/features/inbox/api";
import { collateReactions } from "@/features/inbox/messageContent";
import { MessageBubble } from "@/features/inbox/MessageBubble";
import type { ConversationStatus, InboxFilters } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";
import { useTags } from "@/features/customer-profile/api";
import { useHasPermission } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 25;

function readFilters(params: URLSearchParams): InboxFilters {
  return {
    // Deep-link only (e.g. a future Customer 360 link) — there is no free-text picker for a raw
    // contact id, so this is read from the URL rather than offered as a manual filter control.
    contact: params.get("contact") ?? undefined,
    status: params.get("status") ?? undefined,
    assignee: params.get("assignee") ?? undefined,
    number: params.get("number") ?? undefined,
    tag: params.get("tag") ?? undefined,
    q: params.get("q") ?? undefined,
  };
}

function writeParams(
  filters: InboxFilters,
  conversationId: string | null,
  cursor: string | null,
): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.contact) params.set("contact", filters.contact);
  if (filters.status) params.set("status", filters.status);
  if (filters.assignee) params.set("assignee", filters.assignee);
  if (filters.number) params.set("number", filters.number);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.q) params.set("q", filters.q);
  if (conversationId) params.set("conversation", conversationId);
  if (cursor) params.set("cursor", cursor);
  return params;
}

function contactLabel(contact: { name: string | null; phone: string } | null): string {
  return contact?.name ?? contact?.phone ?? "Unknown contact";
}

function hasActiveFilter(filters: InboxFilters): boolean {
  return Boolean(
    filters.q || filters.status || filters.assignee || filters.number || filters.tag,
  );
}

/**
 * Dedicated Chat History — a read-only workspace over the same conversation/message contract Live
 * Chat and Customer 360 already read (`features/inbox/api.ts`). It reuses those hooks and cache keys
 * verbatim rather than opening a second query authority.
 *
 * Deliberately does not expose assignment, status, tags, notes or sending — those stay Live Chat's
 * job; this route only reproduces the factual record for lookup, review and audit reference. Date
 * range and transcript export are not backed by the current contract and are named as such rather
 * than faked with a disabled control (Doc: MODULE_STATUS.md "Chat History").
 */
export function ChatHistory(): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const cursor = searchParams.get("cursor");
  const selectedId = searchParams.get("conversation");

  const conversations = useConversations(filters, cursor, PAGE_SIZE);
  const assignees = useAssignableUsers();
  const numbers = usePhoneNumbers();
  const tags = useTags();
  const canAudit = useHasPermission("audit:read");

  const selectedConversation = useConversation(selectedId);
  const messages = useMessages(selectedId, 50);

  const rows = conversations.data?.data ?? [];
  const page = conversations.data?.page;
  const tagOptions = (tags.data ?? []).map((tag) => ({
    id: tag.id,
    name: tag.name,
    color: tag.color ?? null,
  }));
  const assigneeName = new Map((assignees.data ?? []).map((user) => [user.id, user.full_name]));
  const filtersActive = hasActiveFilter(filters);

  function applyFilters(next: InboxFilters): void {
    setSearchParams(writeParams(next, selectedId, null));
  }

  function select(conversationId: string | null): void {
    setSearchParams(writeParams(filters, conversationId, cursor));
  }

  function goToCursor(next: string): void {
    setSearchParams(writeParams(filters, selectedId, next));
  }

  const flatMessages = (messages.data?.pages ?? []).flatMap((p) => p.data);
  const { thread: orderedMessages } = collateReactions([...flatMessages].reverse());
  const thread = selectedConversation.data ?? null;

  return (
    <div className="flex h-full min-h-0 flex-col bg-canvas">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-surface px-4 py-3.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-text-primary">
            <History aria-hidden className="h-4 w-4 text-accent" />
            Chat History
          </div>
          <p className="mt-1 max-w-2xl text-xs text-text-secondary">
            Read-only conversation and message history. To reply, assign, tag or resolve a
            conversation, open it in Live Chat. Date-range filtering and transcript export are not
            available yet.
          </p>
        </div>
        {canAudit ? (
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<ShieldCheck aria-hidden className="h-4 w-4" />}
            onClick={() => navigate("/admin/audit")}
          >
            Open audit trail
          </Button>
        ) : null}
      </header>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div
          className={`${selectedId ? "hidden lg:flex" : "flex"} w-full shrink-0 flex-col border-b border-border bg-surface lg:w-[380px] lg:border-b-0 lg:border-r`}
        >
          <div className="space-y-3 border-b border-border p-3">
            <Input
              id="chat-history-search"
              type="search"
              value={filters.q ?? ""}
              onChange={(event) =>
                applyFilters({ ...filters, q: event.target.value || undefined })
              }
              placeholder="Search by customer name or number…"
              aria-label="Search chat history"
              leadingIcon={<Search aria-hidden className="h-4 w-4" />}
            />

            <div className="grid grid-cols-2 gap-2">
              <Field htmlFor="chat-history-status" label="Status">
                <Select
                  id="chat-history-status"
                  value={filters.status ?? ""}
                  onChange={(event) =>
                    applyFilters({ ...filters, status: event.target.value || undefined })
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
              <Field htmlFor="chat-history-assignee" label="Agent">
                <Select
                  id="chat-history-assignee"
                  value={filters.assignee ?? ""}
                  onChange={(event) =>
                    applyFilters({ ...filters, assignee: event.target.value || undefined })
                  }
                >
                  <option value="">Anyone</option>
                  <option value="unassigned">Unassigned</option>
                  {(assignees.data ?? []).map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field htmlFor="chat-history-number" label="Channel" className="col-span-2">
                <Select
                  id="chat-history-number"
                  value={filters.number ?? ""}
                  onChange={(event) =>
                    applyFilters({ ...filters, number: event.target.value || undefined })
                  }
                >
                  <option value="">All numbers</option>
                  {(numbers.data ?? []).map((number) => (
                    <option key={number.id} value={number.id}>
                      {number.display_number}
                      {number.verified_name ? ` — ${number.verified_name}` : ""}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            {tagOptions.length > 0 ? (
              <div>
                <p className="mb-1.5 text-xs font-medium text-text-secondary">Tag</p>
                <div className="flex flex-wrap gap-1">
                  {tagOptions.map((tag) => {
                    const active = filters.tag === tag.id;
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        aria-pressed={active}
                        onClick={() =>
                          applyFilters({ ...filters, tag: active ? undefined : tag.id })
                        }
                        className={`rounded-full ${active ? "ring-2 ring-focus" : ""}`}
                      >
                        <TagChip name={tag.name} color={tag.color} />
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {conversations.isLoading ? (
              <div className="p-4">
                <Spinner label="Loading conversation history…" />
              </div>
            ) : conversations.isError ? (
              <div className="p-3">
                <ErrorState
                  message={apiErrorMessage(conversations.error)}
                  onRetry={() => void conversations.refetch()}
                />
              </div>
            ) : rows.length === 0 ? (
              filtersActive ? (
                <EmptyState
                  title="No conversations match"
                  description="No conversation history matches these filters."
                  action={
                    <Button variant="secondary" onClick={() => applyFilters({})}>
                      Clear filters
                    </Button>
                  }
                />
              ) : (
                <EmptyState
                  title="No conversation history yet"
                  description="A persisted WhatsApp thread will appear here after the first inbound or outbound message."
                />
              )
            ) : (
              <ul aria-label="Conversation history" className="divide-y divide-border">
                {rows.map((conversation) => {
                  const selected = conversation.id === selectedId;
                  const name = contactLabel(conversation.contact);
                  return (
                    <li key={conversation.id}>
                      <button
                        type="button"
                        aria-current={selected ? "true" : undefined}
                        onClick={() => select(conversation.id)}
                        className={`w-full px-3 py-3 text-left transition-colors hover:bg-hover ${selected ? "bg-surface-2" : ""}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="truncate text-sm font-semibold text-text-primary">
                            {name}
                          </span>
                          <time className="shrink-0 text-[11px] text-text-disabled">
                            {formatDateTime(conversation.last_message_at)}
                          </time>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-text-secondary">
                          {conversation.last_message_preview ?? "No messages"}
                        </p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <Badge
                            tone={conversation.status === "resolved" ? "neutral" : "success"}
                            dot
                          >
                            {STATUS_LABELS[conversation.status as ConversationStatus] ??
                              conversation.status}
                          </Badge>
                          {conversation.tags.slice(0, 2).map((tag) => (
                            <TagChip key={tag.id} name={tag.name} color={tag.color} />
                          ))}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <Pagination
            compact
            label="Conversation history pagination"
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
        </div>

        <div className={`${selectedId ? "flex" : "hidden lg:flex"} min-h-0 min-w-0 flex-1 flex-col`}>
          {!selectedId ? (
            <div className="p-6">
              <EmptyState
                title="Select a conversation"
                description="Choose a conversation to read its full message history."
              />
            </div>
          ) : (
            <div className="flex h-full min-h-0 flex-col">
              <button
                type="button"
                onClick={() => select(null)}
                className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3 text-sm font-semibold text-text-primary lg:hidden"
              >
                <ArrowLeft aria-hidden className="h-4 w-4" /> Back to conversation history
              </button>

              {selectedConversation.isLoading ? (
                <div className="p-6">
                  <Spinner label="Loading conversation…" />
                </div>
              ) : selectedConversation.isError || !thread ? (
                <div className="p-6">
                  <ErrorState
                    message={apiErrorMessage(selectedConversation.error)}
                    onRetry={() => void selectedConversation.refetch()}
                  />
                </div>
              ) : (
                <>
                  <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface px-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-text-primary">
                        {contactLabel(thread.contact)}
                      </p>
                      <p className="truncate text-xs text-text-secondary">
                        {thread.contact?.phone} ·{" "}
                        {STATUS_LABELS[thread.status as ConversationStatus] ?? thread.status} ·{" "}
                        {thread.assigned_to
                          ? (assigneeName.get(thread.assigned_to) ?? "Assigned agent")
                          : "Unassigned"}
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      leftIcon={<ExternalLink aria-hidden className="h-4 w-4" />}
                      onClick={() => navigate(`/inbox?conversation=${selectedId}`)}
                    >
                      Open in Live Chat
                    </Button>
                  </header>

                  <div className="min-h-0 flex-1 overflow-y-auto bg-canvas/50 p-3 sm:p-4">
                    {messages.isLoading ? (
                      <Spinner label="Loading messages…" />
                    ) : messages.isError ? (
                      <ErrorState
                        message={apiErrorMessage(messages.error)}
                        onRetry={() => void messages.refetch()}
                      />
                    ) : orderedMessages.length === 0 ? (
                      <EmptyState
                        compact
                        title="No messages in this thread"
                        description="Conversation metadata is persisted, but the message ledger has no visible entries."
                      />
                    ) : (
                      <ul className="space-y-2">
                        {messages.hasNextPage ? (
                          <li className="flex justify-center">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => void messages.fetchNextPage()}
                              disabled={messages.isFetchingNextPage}
                            >
                              {messages.isFetchingNextPage ? "Loading…" : "Load older messages"}
                            </Button>
                          </li>
                        ) : null}
                        {orderedMessages.map((message) => (
                          <MessageBubble
                            key={message.id}
                            message={message}
                            canReact={false}
                            onReact={() => undefined}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
