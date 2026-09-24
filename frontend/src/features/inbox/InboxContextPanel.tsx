import { ChevronDown, ExternalLink, Merge, Pin, PinOff, X } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/ui";
import { AiFoundationPanel } from "@/features/ai";
import { ConversationTags } from "@/features/inbox/ConversationControls";
import { NotesPanel } from "@/features/inbox/NotesPanel";
import type { Conversation, TagSummary } from "@/features/inbox/types";
import { connectorLabel, STATUS_LABELS, type ConversationStatus } from "@/features/inbox/types";

interface Props {
  conversation: Conversation;
  tags?: TagSummary[];
  pinned: boolean;
  onTogglePinned: () => void;
  onClose?: () => void;
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return `${date.toLocaleDateString("en-GB")}, ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

/** One white 48px accordion row from the reference profile column. */
function Section({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }): JSX.Element {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <div className="rounded-md bg-surface">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
        className="flex h-12 w-full items-center justify-between px-4 text-left text-base text-[#4a4a4a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus dark:text-text-primary"
      >
        {title}
        <ChevronDown aria-hidden className={`h-6 w-6 text-black/55 transition-transform duration-200 dark:text-text-secondary ${open ? "rotate-180" : ""}`} />
      </button>
      <div id={id} className={`grid transition-[grid-template-rows] duration-200 ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className={`min-h-0 overflow-hidden ${open ? "visible" : "invisible"}`}>
          <div className="px-4 pb-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

/** The reference "Chat Profile" column: identity, a facts card, then collapsible sections. */
export function InboxContextPanel({ conversation, tags = [], pinned, onTogglePinned, onClose = () => undefined }: Props): JSX.Element {
  const contact = conversation.contact;
  const name = contact?.name ?? contact?.phone ?? "Unknown customer";
  const status = STATUS_LABELS[conversation.status as ConversationStatus] ?? conversation.status;
  const facts: [string, ReactNode][] = [
    ["Status", status],
    ["Last Active", formatWhen(conversation.last_message_at)],
    ["Unread Messages", conversation.unread_count],
    ["Assigned To", conversation.assigned_to ?? "Unassigned"],
    ["WA Conversation", conversation.window.is_open ? "Active" : "Inactive"],
    ["Channel", connectorLabel(conversation)],
  ];

  return (
    <aside aria-label="Conversation details" className="absolute inset-y-0 right-0 z-30 flex w-full shrink-0 flex-col overflow-hidden bg-[#f8f8f8] shadow-2xl dark:bg-surface sm:w-[340px] lg:relative lg:inset-auto lg:shadow-none">
      <div className="relative flex h-[50px] shrink-0 items-center justify-center bg-[var(--color-nav-bg)] text-white">
        <h2 className="text-base font-normal">Chat Profile</h2>
        <button type="button" aria-label="Close details" onClick={onClose} className="absolute right-2 flex h-9 w-9 items-center justify-center rounded-full text-white/80 hover:bg-white/10 hover:text-white xl:hidden">
          <X aria-hidden className="h-5 w-5" />
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-6">
        <div className="flex items-center justify-center gap-6">
          <span className="flex h-[55px] w-[55px] shrink-0 items-center justify-center rounded-full bg-[#ffa500] text-[30px] text-white">
            {name.trim()[0]?.toUpperCase() ?? "?"}
          </span>
          <div className="min-w-0">
            <h3 className="truncate px-2 py-1 text-xl font-normal text-black dark:text-text-primary">{name}</h3>
            <p className="px-2 text-sm text-black dark:text-text-secondary">{contact?.phone ?? "No phone available"}</p>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-2 gap-y-1 rounded-[8px] bg-[#ebf5f3] p-4 text-xs dark:bg-accent-soft">
          {facts.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-[#4a4a4a] dark:text-text-secondary">{label}</dt>
              <dd className="truncate text-black dark:text-text-primary">{value}</dd>
            </div>
          ))}
        </dl>

        <Section title="Tags" defaultOpen>
          <ConversationTags conversation={conversation} tags={tags} />
        </Section>
        <Section title="Notes">
          <NotesPanel conversationId={conversation.id} />
        </Section>
        <Section title="AI Assist">
          <AiFoundationPanel compact capabilities={["reply", "summary"]} context={`conversation with ${name}`} />
        </Section>

        <div className="grid grid-cols-2 gap-2">
          <button type="button" onClick={onTogglePinned} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-surface text-sm text-[#4a4a4a] transition-colors hover:bg-hover dark:text-text-primary">
            {pinned ? <PinOff aria-hidden className="h-4 w-4" /> : <Pin aria-hidden className="h-4 w-4" />}
            {pinned ? "Unpin" : "Pin"}
          </button>
          <button type="button" disabled title="Merging chats is not available yet" className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-surface text-sm text-text-disabled disabled:cursor-not-allowed">
            <Merge aria-hidden className="h-4 w-4" /> Merge
          </button>
        </div>

        {contact ? (
          <Link to={`/contacts/${contact.id}`} className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-[var(--color-nav-bg)] px-3 text-sm font-medium text-white transition-colors hover:bg-[#08393d]">
            Open Customer 360 <ExternalLink aria-hidden className="h-3.5 w-3.5" />
          </Link>
        ) : <EmptyState compact title="No linked contact" />}
      </div>
    </aside>
  );
}
