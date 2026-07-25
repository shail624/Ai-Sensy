import { Clock3, ExternalLink, Merge, Pin, PinOff, UserRound } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AiFoundationPanel } from "@/features/ai";
import { NotesPanel } from "@/features/inbox/NotesPanel";
import type { Conversation } from "@/features/inbox/types";
import { Badge, EmptyState, TagChip } from "@/components/ui";

type ContextTab = "customer" | "notes" | "ai";

interface Props {
  conversation: Conversation;
  pinned: boolean;
  onTogglePinned: () => void;
}

/** Customer context and collaboration live beside the thread without duplicating Customer 360. */
export function InboxContextPanel({ conversation, pinned, onTogglePinned }: Props): JSX.Element {
  const [tab, setTab] = useState<ContextTab>("customer");
  const contact = conversation.contact;
  const name = contact?.name ?? contact?.phone ?? "Unknown customer";

  return (
    <aside className="flex w-full shrink-0 flex-col overflow-hidden border-t border-border bg-surface lg:w-80 lg:border-l lg:border-t-0">
      <nav aria-label="Conversation context" role="tablist" className="flex gap-1 border-b border-border p-2">
        {(["customer", "notes", "ai"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`min-h-9 flex-1 rounded-lg px-2 text-xs font-semibold capitalize ${tab === key ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-hover"}`}
          >
            {key}
          </button>
        ))}
      </nav>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {tab === "customer" ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-surface-subtle p-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <UserRound aria-hidden className="h-5 w-5" />
              </span>
              <h3 className="mt-3 text-sm font-semibold text-text-primary">{name}</h3>
              <p className="mt-0.5 text-xs text-text-secondary">{contact?.phone ?? "No phone available"}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge tone={conversation.window.is_open ? "success" : "neutral"} dot>
                  {conversation.window.is_open ? "Reply window open" : "Template required"}
                </Badge>
                <Badge tone={conversation.unread_count > 0 ? "accent" : "neutral"}>
                  {conversation.unread_count > 0 ? `${conversation.unread_count} unread` : "Read"}
                </Badge>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Labels</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {conversation.tags.length > 0
                  ? conversation.tags.map((tag) => <TagChip key={tag.id} name={tag.name} color={tag.color} />)
                  : <span className="text-xs text-text-secondary">No labels yet</span>}
              </div>
            </div>

            <dl className="divide-y divide-border rounded-xl border border-border px-3">
              <div className="flex items-center justify-between gap-3 py-2.5 text-xs"><dt className="text-text-secondary">Assignment</dt><dd className="font-medium text-text-primary">{conversation.assigned_to ?? "Unassigned"}</dd></div>
              <div className="flex items-center justify-between gap-3 py-2.5 text-xs"><dt className="text-text-secondary">Lifecycle</dt><dd className="font-medium capitalize text-text-primary">{conversation.status}</dd></div>
              <div className="flex items-center justify-between gap-3 py-2.5 text-xs"><dt className="text-text-secondary">Last interaction</dt><dd className="font-medium text-text-primary">{conversation.last_message_at ? new Date(conversation.last_message_at).toLocaleString() : "No messages"}</dd></div>
            </dl>

            <div className="grid grid-cols-2 gap-2">
              <button type="button" onClick={onTogglePinned} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-border text-xs font-semibold text-text-primary hover:bg-hover">
                {pinned ? <PinOff aria-hidden className="h-4 w-4" /> : <Pin aria-hidden className="h-4 w-4" />}
                {pinned ? "Unpin" : "Pin"}
              </button>
              <button type="button" disabled title="Conversation merge requires an additive audited domain contract" className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-border text-xs font-semibold text-text-disabled disabled:cursor-not-allowed">
                <Merge aria-hidden className="h-4 w-4" /> Merge
              </button>
            </div>
            <p className="flex gap-2 text-[11px] leading-relaxed text-text-disabled"><Clock3 aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />Snooze is available through conversation status. Timed wake-up is not simulated without a server-owned timer.</p>

            {contact ? (
              <Link to={`/contacts/${contact.id}`} className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-xl bg-accent px-3 text-xs font-semibold text-accent-fg">
                Open Customer 360 <ExternalLink aria-hidden className="h-3.5 w-3.5" />
              </Link>
            ) : <EmptyState compact title="No linked contact" />}
          </div>
        ) : null}

        {tab === "notes" ? <NotesPanel conversationId={conversation.id} /> : null}
        {tab === "ai" ? <AiFoundationPanel compact capabilities={["reply", "summary"]} context={`conversation with ${name}`} /> : null}
      </div>
    </aside>
  );
}
