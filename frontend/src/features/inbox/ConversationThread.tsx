import { ArrowLeft, MailCheck, MessageCircle, PanelRightOpen, QrCode, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
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
import { InterventionActions } from "@/features/inbox/InterventionActions";
import type { TagSummary } from "@/features/inbox/types";
import { connectorLabel, isWahaConversation } from "@/features/inbox/types";
import { useInboxOperations } from "@/features/settings/api";
import { useAuth, useHasPermission } from "@/lib/auth";
import { useMediaQuery } from "@/lib/useMediaQuery";

interface Props {
  conversationId: string;
  /** Closes the chat (the reference header's back arrow). */
  onBack?: () => void;
  tags: TagSummary[];
  pinned?: boolean;
  onTogglePinned?: () => void;
}

/** The active chat keeps daily reply controls visible and moves secondary context one click away. */
export function ConversationThread({ conversationId, onBack, tags, pinned = false, onTogglePinned = () => undefined }: Props): JSX.Element {
  const { user } = useAuth();
  const conversation = useConversation(conversationId);
  const messages = useMessages(conversationId);
  const markRead = useMarkRead(conversationId);
  const operations = useInboxOperations();
  const reaction = useSendReaction(conversationId);
  const canSend = useHasPermission("messages:send");
  // The reference keeps Chat Profile beside every open chat on wide screens.
  const wide = useMediaQuery("(min-width: 1280px)");
  const [contextOpen, setContextOpen] = useState(wide);
  useEffect(() => setContextOpen(wide), [wide]);

  const unread = conversation.data?.unread_count ?? 0;
  const markReadMutate = markRead.mutate;
  const autoMarkRead = operations.data?.auto_mark_read === true;
  const canMarkReadManually = operations.isSuccess && !autoMarkRead && unread > 0;

  useEffect(() => {
    if (autoMarkRead && unread > 0) markReadMutate(undefined);
  }, [autoMarkRead, conversationId, unread, markReadMutate]);

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
      <header className="flex h-[50px] shrink-0 items-center gap-1.5 bg-[var(--color-nav-bg)] pr-2 text-white">
        {onBack ? (
          <button type="button" aria-label="Close chat" title="Close chat" onClick={onBack} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70">
            <ArrowLeft aria-hidden className="h-6 w-6" />
          </button>
        ) : <span className="w-3" />}
        <h2 className="min-w-0 flex-1 truncate text-base font-normal">
          {contactName}
          {thread.contact?.phone && thread.contact.phone !== contactName ? ` (${thread.contact.phone})` : ""}
        </h2>
        <span title={connectorLabel(thread)} className="inline-flex shrink-0 items-center rounded-full bg-white/10 px-2 py-0.5 text-[11px]">
          {isWahaConversation(thread) ? <QrCode aria-hidden className="mr-1 h-3 w-3" /> : <ShieldCheck aria-hidden className="mr-1 h-3 w-3" />}
          {connectorLabel(thread)}
        </span>
        <button
          type="button"
          aria-expanded={contextOpen}
          onClick={() => setContextOpen((open) => !open)}
          title="Chat Profile"
          className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-xs text-white/85 hover:bg-white/10 hover:text-white xl:hidden"
        >
          <PanelRightOpen aria-hidden className="h-4 w-4" />
          <span className="hidden sm:inline">Details</span>
        </button>
      </header>

      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-[#f2f2f2] bg-[#fdfffc] px-3 py-2 dark:border-border dark:bg-surface">
        <div className="grid min-w-0 flex-1 grid-cols-2 gap-2 sm:max-w-md">
          <StatusControl conversation={thread} />
          <AssignmentControl conversation={thread} />
        </div>
        {isWahaConversation(thread) ? null : (
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${thread.window.is_open ? "bg-success-soft text-success-on-soft" : "bg-surface-2 text-text-secondary"}`}>
            <MessageCircle aria-hidden className="h-3 w-3" />
            {thread.window.is_open ? "Reply open" : "Template only"}
          </span>
        )}
        {canMarkReadManually ? (
          <button
            type="button"
            aria-label="Mark read"
            disabled={markRead.isPending}
            onClick={() => markReadMutate(undefined)}
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-[rgba(10,71,76,0.5)] px-3 text-xs font-medium text-[var(--color-nav-bg)] transition hover:bg-[#ebf5f3] disabled:opacity-50 dark:text-accent"
          >
            <MailCheck aria-hidden className="h-4 w-4" />
            <span className="hidden sm:inline">Mark read</span>
          </button>
        ) : null}
        <InterventionActions conversation={thread} currentUserId={user?.id} />
      </div>

      <div className="relative flex min-h-0 flex-1">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="chat-wallpaper flex-1 overflow-y-auto px-3 pb-2 pt-3 sm:px-4">
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
                {ordered.map((message, index) => {
                  const day = new Date(message.created_at).toLocaleDateString("en-GB");
                  const previous = index > 0 ? new Date(ordered[index - 1]!.created_at).toLocaleDateString("en-GB") : null;
                  return [
                    day !== previous ? (
                      <li key={`day-${day}`} className="flex justify-center py-1">
                        <span className="rounded-md bg-[#fbf9f3] px-2.5 py-1 text-xs text-[#7f6a71] shadow-[0_1px_0.5px_rgba(0,0,0,0.08)] dark:bg-surface dark:text-text-secondary">{day}</span>
                      </li>
                    ) : null,
                  <MessageBubble
                    key={message.id}
                    contactInitial={contactName.trim()[0]?.toUpperCase() ?? "?"}
                    message={message}
                    canReact={canSend}
                    reactions={reactions.get(message.id)}
                    onReact={(emoji) => reaction.mutate({ messageId: message.id, emoji })}
                  />,
                  ];
                })}
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
