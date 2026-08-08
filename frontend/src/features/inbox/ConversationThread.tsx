import { MessageCircle, PanelRightOpen, QrCode, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge, EmptyState, ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useConversation,
  useMarkRead,
  useMessages,
  useSendReaction,
} from "@/features/inbox/api";
import { AssignmentControl, StatusControl } from "@/features/inbox/ConversationControls";
import { collateReactions } from "@/features/inbox/messageContent";
import { MessageBubble } from "@/features/inbox/MessageBubble";
import { MessageComposer } from "@/features/inbox/MessageComposer";
import { InboxContextPanel } from "@/features/inbox/InboxContextPanel";
import type { TagSummary } from "@/features/inbox/types";
import { connectorLabel, isWahaConversation } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";

interface Props {
  conversationId: string;
  tags: TagSummary[];
  pinned?: boolean;
  onTogglePinned?: () => void;
}

/** The active chat keeps daily reply controls visible and moves secondary context one click away. */
export function ConversationThread({ conversationId, tags, pinned = false, onTogglePinned = () => undefined }: Props): JSX.Element {
  const conversation = useConversation(conversationId);
  const messages = useMessages(conversationId);
  const markRead = useMarkRead(conversationId);
  const reaction = useSendReaction(conversationId);
  const canSend = useHasPermission("messages:send");
  const [contextOpen, setContextOpen] = useState(false);

  const unread = conversation.data?.unread_count ?? 0;
  const markReadMutate = markRead.mutate;

  useEffect(() => {
    if (unread > 0) markReadMutate(undefined);
  }, [conversationId, unread, markReadMutate]);

  if (conversation.isLoading) {
    return <div className="p-6"><Spinner label="Loading conversation…" /></div>;
  }

  if (conversation.isError || !conversation.data) {
    return <div className="p-6"><ErrorState message={apiErrorMessage(conversation.error)} onRetry={() => void conversation.refetch()} /></div>;
  }

  const thread = conversation.data;
  const flat = (messages.data?.pages ?? []).flatMap((page) => page.data);
  const { thread: ordered, reactions } = collateReactions([...flat].reverse());
  const contactName = thread.contact?.name ?? thread.contact?.phone ?? "Unknown contact";

  return (
    <div className="relative flex h-full min-w-0 flex-col overflow-hidden bg-surface">
      <header className="border-b border-border bg-surface px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
              <UserRound aria-hidden className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-bold text-text-primary">{contactName}</h2>
              <div className="mt-0.5 flex flex-wrap items-center gap-2">
                <p className="truncate text-xs text-text-secondary">{thread.contact?.phone}</p>
                <Badge tone={isWahaConversation(thread) ? "info" : "neutral"}>
                  {isWahaConversation(thread) ? (
                    <QrCode aria-hidden className="mr-1 h-3 w-3" />
                  ) : (
                    <ShieldCheck aria-hidden className="mr-1 h-3 w-3" />
                  )}
                  {connectorLabel(thread)}
                </Badge>
                {isWahaConversation(thread) ? null : (
                  <Badge tone={thread.window.is_open ? "success" : "neutral"}>
                    <MessageCircle aria-hidden className="mr-1 h-3 w-3" />
                    {thread.window.is_open ? "Reply open" : "Template only"}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            aria-expanded={contextOpen}
            onClick={() => setContextOpen((open) => !open)}
            className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl border px-3 text-xs font-semibold transition ${contextOpen ? "border-accent bg-accent-soft text-accent" : "border-border text-text-secondary hover:bg-hover"}`}
          >
            <PanelRightOpen aria-hidden className="h-4 w-4" />
            <span className="hidden sm:inline">Details</span>
          </button>
        </div>

        <div className="mt-3 grid max-w-xl grid-cols-2 gap-2">
          <StatusControl conversation={thread} />
          <AssignmentControl conversation={thread} />
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto bg-canvas/50 p-3 sm:p-4">
            {messages.isLoading ? (
              <Spinner label="Loading messages…" />
            ) : messages.isError ? (
              <ErrorState message={apiErrorMessage(messages.error)} onRetry={() => void messages.refetch()} />
            ) : ordered.length === 0 ? (
              <EmptyState title="No messages yet" description="Start the conversation when the reply window allows it." />
            ) : (
              <ul className="space-y-2">
                {messages.hasNextPage ? (
                  <li className="flex justify-center">
                    <button type="button" onClick={() => void messages.fetchNextPage()} disabled={messages.isFetchingNextPage} className="rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-semibold hover:bg-hover disabled:opacity-50">
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
            {reaction.error ? <div className="mt-2"><ErrorState message={apiErrorMessage(reaction.error)} /></div> : null}
          </div>
          <MessageComposer conversation={thread} />
        </div>

        {contextOpen ? (
          <InboxContextPanel
            conversation={thread}
            tags={tags}
            pinned={pinned}
            onTogglePinned={onTogglePinned}
            onClose={() => setContextOpen(false)}
          />
        ) : null}
      </div>
    </div>
  );
}
