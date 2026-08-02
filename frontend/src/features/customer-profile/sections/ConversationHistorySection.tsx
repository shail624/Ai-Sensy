import { ExternalLink, MessageCircle, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Section, Skeleton } from "@/components/ui";
import { apiErrorMessage, useConversations, useMessages } from "@/features/inbox/api";
import { collateReactions } from "@/features/inbox/messageContent";
import { MessageBubble } from "@/features/inbox/MessageBubble";
import { useHasPermission } from "@/lib/auth";

/** Read-only Customer 360 projection over the existing Inbox and message ledger authorities. */
export function ConversationHistorySection({ contactId }: { contactId: string }): JSX.Element {
  const navigate = useNavigate();
  const canRead = useHasPermission("inbox:read");
  const conversations = useConversations({ contact: contactId }, null, 20, canRead);
  const rows = useMemo(() => conversations.data?.data ?? [], [conversations.data?.data]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeId = rows.some((row) => row.id === selectedId) ? selectedId : (rows[0]?.id ?? null);
  const messages = useMessages(canRead ? activeId : null, 50);

  useEffect(() => {
    if (!selectedId && rows[0]) setSelectedId(rows[0].id);
  }, [rows, selectedId]);

  if (!canRead) {
    return (
      <Section title="WhatsApp conversations" description="Conversation access follows Inbox permissions.">
        <EmptyState compact title="Conversation history is restricted" description="Your role cannot read this customer's WhatsApp threads." />
      </Section>
    );
  }

  if (conversations.isLoading) {
    return <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]"><Skeleton className="h-72 w-full" /><Skeleton className="h-72 w-full" /></div>;
  }

  if (conversations.isError) {
    return <ErrorState message={apiErrorMessage(conversations.error)} onRetry={() => void conversations.refetch()} />;
  }

  if (rows.length === 0) {
    return (
      <Section title="WhatsApp conversations" description="Exact contact-scoped history from the shared Inbox ledger.">
        <EmptyState compact title="No conversations yet" description="A persisted WhatsApp thread will appear here after the first inbound or governed outbound message." />
      </Section>
    );
  }

  const flat = (messages.data?.pages ?? []).flatMap((page) => page.data);
  const { thread } = collateReactions([...flat].reverse());
  const active = (rows.find((row) => row.id === activeId) ?? rows[0])!;

  return (
    <div className="grid min-h-[32rem] overflow-hidden rounded-2xl border border-border bg-surface shadow-sm lg:grid-cols-[18rem_minmax(0,1fr)]">
      <section aria-label="Customer conversations" className="border-b border-border lg:border-b-0 lg:border-r">
        <header className="border-b border-border px-4 py-3.5">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary"><MessageCircle aria-hidden className="h-4 w-4 text-accent" />WhatsApp history</div>
          <p className="mt-1 text-xs text-text-secondary">{rows.length} persisted {rows.length === 1 ? "thread" : "threads"}</p>
        </header>
        <div className="max-h-64 overflow-y-auto p-2 lg:max-h-[30rem]">
          {rows.map((row) => (
            <button
              key={row.id}
              type="button"
              aria-pressed={row.id === active.id}
              onClick={() => setSelectedId(row.id)}
              className={`mb-1 w-full rounded-xl border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${row.id === active.id ? "border-accent bg-accent-soft" : "border-transparent hover:bg-hover"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <Badge tone={row.status === "open" ? "success" : row.status === "pending" ? "warning" : "neutral"} dot>{row.status}</Badge>
                <time className="text-[11px] text-text-disabled">{row.last_message_at ? new Date(row.last_message_at).toLocaleDateString() : "No messages"}</time>
              </div>
              <p className="mt-2 truncate text-sm font-medium text-text-primary">{row.last_message_preview ?? "No message preview"}</p>
              <p className="mt-1 truncate text-xs text-text-secondary">{row.assigned_to ? "Assigned conversation" : "Unassigned"}{row.unread_count ? ` · ${row.unread_count} unread` : ""}</p>
            </button>
          ))}
        </div>
      </section>

      <section aria-label="Selected conversation messages" className="flex min-w-0 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent"><UserRound aria-hidden className="h-4 w-4" /></span>
            <div className="min-w-0"><p className="truncate text-sm font-semibold text-text-primary">{active.contact?.name ?? active.contact?.phone ?? "Customer thread"}</p><p className="truncate text-xs text-text-secondary">{active.channel_type} · {active.window.is_open ? "reply window open" : "template required"}</p></div>
          </div>
          <Button variant="secondary" leftIcon={<ExternalLink aria-hidden className="h-4 w-4" />} onClick={() => navigate(`/inbox?conversation=${active.id}`)}>Open in Inbox</Button>
        </header>
        <div className="min-h-72 flex-1 overflow-y-auto bg-canvas/50 p-3 sm:p-4">
          {messages.isLoading ? <div className="space-y-3"><Skeleton className="h-14 w-2/3" /><Skeleton className="ml-auto h-14 w-3/5" /><Skeleton className="h-14 w-1/2" /></div> : messages.isError ? <ErrorState message={apiErrorMessage(messages.error)} onRetry={() => void messages.refetch()} /> : thread.length === 0 ? <EmptyState compact title="No messages in this thread" description="Conversation metadata is persisted, but the message ledger has no visible entries." /> : <ul className="space-y-2">{messages.hasNextPage ? <li className="text-center"><Button variant="secondary" onClick={() => void messages.fetchNextPage()} disabled={messages.isFetchingNextPage}>{messages.isFetchingNextPage ? "Loading…" : "Load older messages"}</Button></li> : null}{thread.map((message) => <MessageBubble key={message.id} message={message} canReact={false} onReact={() => undefined} />)}</ul>}
        </div>
      </section>
    </div>
  );
}
