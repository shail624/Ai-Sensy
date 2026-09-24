import { Check, Clock3, Pin, PinOff, QrCode, ShieldCheck } from "lucide-react";

import { TagChip } from "@/components/ui";
import { CustomerAvatar } from "@/features/inbox/CustomerAvatar";
import type { Conversation, ConversationStatus } from "@/features/inbox/types";
import { connectorLabel, isWahaConversation, STATUS_LABELS } from "@/features/inbox/types";

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const minutes = Math.round((Date.now() - then) / 60_000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
  return new Date(iso).toLocaleDateString();
}

function displayName(conversation: Conversation): string {
  return conversation.contact?.name ?? conversation.contact?.phone ?? "Unknown contact";
}


function responseSignal(conversation: Conversation): { label: string; className: string } | null {
  if (conversation.unread_count === 0 || !conversation.last_message_at) return null;
  const minutes = Math.max(0, Math.round((Date.now() - new Date(conversation.last_message_at).getTime()) / 60_000));
  if (minutes >= 60) return { label: `${Math.round(minutes / 60)}h waiting`, className: "bg-danger-soft text-danger-on-soft" };
  if (minutes >= 15) return { label: `${minutes}m waiting`, className: "bg-warning-soft text-warning-on-soft" };
  return null;
}

interface Props {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  pinnedIds?: string[];
  onTogglePinned?: (id: string) => void;
  selection?: string[];
  onToggleSelection?: (id: string) => void;
}

/** Compact inbox rail: identity and unread urgency first, secondary metadata on demand. */
export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  pinnedIds = [],
  onTogglePinned = () => undefined,
  selection = [],
  onToggleSelection = () => undefined,
}: Props): JSX.Element {
  const ordered = [...conversations].sort((left, right) => Number(pinnedIds.includes(right.id)) - Number(pinnedIds.includes(left.id)));
  return (
    <ul aria-label="Conversations">
      {ordered.map((conversation) => {
        const selected = conversation.id === selectedId;
        const checked = selection.includes(conversation.id);
        const pinned = pinnedIds.includes(conversation.id);
        const signal = responseSignal(conversation);
        const status = STATUS_LABELS[conversation.status as ConversationStatus] ?? conversation.status;
        return (
          <li key={conversation.id} className="group relative border-b border-[#f2f2f2] dark:border-border">
            <button
              type="button"
              role="checkbox"
              aria-label={`${checked ? "Remove" : "Add"} ${displayName(conversation)} ${checked ? "from" : "to"} bulk selection`}
              aria-checked={checked}
              onClick={() => onToggleSelection(conversation.id)}
              className={`absolute left-2 top-1/2 z-10 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded border transition-opacity ${checked ? "border-accent bg-accent text-accent-fg opacity-100" : "border-border bg-surface text-transparent opacity-0 group-hover:opacity-100 focus:opacity-100"}`}
            >
              <Check aria-hidden className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={() => onSelect(conversation.id)}
              aria-current={selected ? "true" : undefined}
              className={`flex h-[60px] w-full items-center gap-2 pl-2 pr-3 text-left transition-colors duration-150 ${selected ? "bg-[#ebf5f3] dark:bg-accent-soft" : "hover:bg-black/[0.03] dark:hover:bg-hover"}`}
            >
              <span className={`relative shrink-0 transition-opacity ${checked ? "opacity-0" : "group-hover:opacity-0"}`}>
                <CustomerAvatar conversation={conversation} className="h-10 w-10 bg-[#f5efdf] text-xl text-black dark:bg-surface-2 dark:text-text-primary" />
                {conversation.window.is_open ? (
                  <span title="WhatsApp service window is open" className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-[#28c152] ring-2 ring-[#fdfbf7] dark:ring-surface">
                    <span className="sr-only">Window open</span>
                  </span>
                ) : null}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="truncate text-sm text-black dark:text-text-primary">{displayName(conversation)}</span>
                  {conversation.contact?.name && conversation.contact.phone && conversation.contact.name !== conversation.contact.phone ? (
                    <span className="shrink-0 text-[13px] text-[#6e6e6e] dark:text-text-secondary">{conversation.contact.phone}</span>
                  ) : null}
                  <span title={connectorLabel(conversation)} className={`inline-flex shrink-0 ${isWahaConversation(conversation) ? "text-accent" : "text-[#808080]"}`}>
                    {isWahaConversation(conversation) ? <QrCode aria-hidden className="h-3 w-3" /> : <ShieldCheck aria-hidden className="h-3 w-3" />}
                    <span className="sr-only">{connectorLabel(conversation)}</span>
                  </span>
                  <span className="sr-only">{status}</span>
                  {conversation.tags.slice(0, 1).map((tag) => <TagChip key={tag.id} name={tag.name} color={tag.color} />)}
                </span>
                <span className="mt-px block truncate text-xs font-semibold text-[#808080] dark:text-text-secondary">
                  {conversation.last_message_preview ?? "No messages yet"}
                </span>
              </span>
              <span className="flex shrink-0 flex-col items-end gap-1">
                <span className="text-[10px] text-[#808080]">{relativeTime(conversation.last_message_at)}</span>
                {signal ? (
                  <span title="How long this customer has been waiting for a reply" className={`inline-flex items-center gap-1 rounded-full px-1.5 text-[10px] font-semibold ${signal.className}`}>
                    <Clock3 aria-hidden className="h-3 w-3" /> {signal.label}
                  </span>
                ) : null}
              </span>
              {conversation.unread_count > 0 ? (
                <span className="flex h-7 min-w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-nav-bg)] px-1 text-xs text-white">
                  {conversation.unread_count > 99 ? "99+" : conversation.unread_count}
                </span>
              ) : null}
            </button>
            <button
              type="button"
              aria-label={pinned ? "Unpin conversation" : "Pin conversation"}
              aria-pressed={pinned}
              onClick={() => onTogglePinned(conversation.id)}
              className={`absolute right-11 top-1 rounded-md p-1 transition-opacity hover:bg-hover focus:opacity-100 ${pinned ? "text-accent" : "text-text-disabled opacity-0 group-hover:opacity-100"}`}
            >
              {pinned ? <PinOff aria-hidden className="h-3.5 w-3.5" /> : <Pin aria-hidden className="h-3.5 w-3.5" />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
