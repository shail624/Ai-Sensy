import { useEffect } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useConversation,
  useMarkRead,
  useMessages,
  useSendReaction,
} from "@/features/inbox/api";
import {
  AssignmentControl,
  ConversationTags,
  StatusControl,
} from "@/features/inbox/ConversationControls";
import { collateReactions } from "@/features/inbox/messageContent";
import { MessageBubble } from "@/features/inbox/MessageBubble";
import { MessageComposer } from "@/features/inbox/MessageComposer";
import { InboxContextPanel } from "@/features/inbox/InboxContextPanel";
import type { TagSummary } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";

interface Props {
  conversationId: string;
  tags: TagSummary[];
  pinned?: boolean;
  onTogglePinned?: () => void;
}

/** The open conversation: header + controls, message history, composer, and internal notes. */
export function ConversationThread({ conversationId, tags, pinned = false, onTogglePinned = () => undefined }: Props): JSX.Element {
  const conversation = useConversation(conversationId);
  const messages = useMessages(conversationId);
  const markRead = useMarkRead(conversationId);
  const reaction = useSendReaction(conversationId);
  const canSend = useHasPermission("messages:send");

  const unread = conversation.data?.unread_count ?? 0;
  const markReadMutate = markRead.mutate;

  // Opening a thread with unread messages clears the shared counter for the whole team.
  useEffect(() => {
    if (unread > 0) markReadMutate(undefined);
    // Only re-run when the conversation or its unread state changes.
  }, [conversationId, unread, markReadMutate]);

  if (conversation.isLoading) {
    return (
      <div className="p-6">
        <Spinner label="Loading conversation…" />
      </div>
    );
  }

  if (conversation.isError || !conversation.data) {
    return (
      <div className="p-6">
        <ErrorState
          message={apiErrorMessage(conversation.error)}
          onRetry={() => void conversation.refetch()}
        />
      </div>
    );
  }

  const thread = conversation.data;
  // Pages arrive newest-first; flatten then reverse so the thread reads downward, and lift
  // reaction messages onto the messages they annotate.
  const flat = (messages.data?.pages ?? []).flatMap((page) => page.data);
  const { thread: ordered, reactions } = collateReactions([...flat].reverse());

  return (
    <div className="flex h-full min-w-0 flex-col">
      <header className="border-b border-border p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-text-primary">
              {thread.contact?.name ?? thread.contact?.phone ?? "Unknown contact"}
            </h2>
            <p className="text-xs text-text-secondary">{thread.contact?.phone}</p>
          </div>
          {thread.contact ? (
            <Link
              to={`/contacts/${thread.contact.id}`}
              className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
            >
              Open customer
            </Link>
          ) : null}
        </div>

        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <StatusControl conversation={thread} />
          <AssignmentControl conversation={thread} />
          <ConversationTags conversation={thread} tags={tags} />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto p-3">
            {messages.isLoading ? (
              <Spinner label="Loading messages…" />
            ) : messages.isError ? (
              <ErrorState
                message={apiErrorMessage(messages.error)}
                onRetry={() => void messages.refetch()}
              />
            ) : ordered.length === 0 ? (
              <EmptyState title="No messages yet" />
            ) : (
              <ul className="space-y-2">
                {messages.hasNextPage ? (
                  <li className="flex justify-center">
                    <button
                      type="button"
                      onClick={() => void messages.fetchNextPage()}
                      disabled={messages.isFetchingNextPage}
                      className="rounded-md border border-border px-3 py-1 text-xs hover:bg-hover disabled:opacity-50"
                    >
                      {messages.isFetchingNextPage ? "Loading…" : "Load older messages"}
                    </button>
                  </li>
                ) : null}
                {ordered.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    canReact={canSend}
                    reactions={reactions.get(message.id)}
                    onReact={(emoji) => reaction.mutate({ messageId: message.id, emoji })}
                  />
                ))}
              </ul>
            )}
            {reaction.error ? (
              <div className="mt-2">
                <ErrorState message={apiErrorMessage(reaction.error)} />
              </div>
            ) : null}
          </div>

          <MessageComposer conversation={thread} />
        </div>

        <InboxContextPanel conversation={thread} pinned={pinned} onTogglePinned={onTogglePinned} />
      </div>
    </div>
  );
}
