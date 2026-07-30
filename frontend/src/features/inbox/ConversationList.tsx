import { Check, Clock3, MessageCircle, Pin, PinOff } from "lucide-react";

import { TagChip } from "@/components/ui";
import type { Conversation, ConversationStatus } from "@/features/inbox/types";
import { STATUS_LABELS } from "@/features/inbox/types";

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

function initials(conversation: Conversation): string {
  return displayName(conversation)
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
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
    <ul className="divide-y divide-border" aria-label="Conversations">
      {ordered.map((conversation) => {
        const selected = conversation.id === selectedId;
        const checked = selection.includes(conversation.id);
        const pinned = pinnedIds.includes(conversation.id);
        const signal = responseSignal(conversation);
        return (
          <li key={conversation.id} className="group relative">
            <button
              type="button"
              role="checkbox"
              aria-label={`${checked ? "Remove" : "Add"} ${displayName(conversation)} ${checked ? "from" : "to"} bulk selection`}
              aria-checked={checked}
              onClick={() => onToggleSelection(conversation.id)}
              className={`absolute left-2 top-3 z-10 flex h-5 w-5 items-center justify-center rounded border transition-opacity ${checked ? "border-accent bg-accent text-accent-fg" : "border-border bg-surface text-transparent opacity-0 group-hover:opacity-100 focus:opacity-100"}`}
            >
              <Check aria-hidden className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={() => onSelect(conversation.id)}
              aria-current={selected ? "true" : undefined}
              className={`w-full py-3 pl-9 pr-9 text-left transition-colors hover:bg-hover ${selected ? "bg-surface-2" : ""}`}
            >
              <div className="flex gap-2.5">
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${selected ? "bg-accent text-accent-fg" : "bg-accent-soft text-accent"}`}>
                  {initials(conversation)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-text-primary">{displayName(conversation)}</span>
                    <span className="shrink-0 text-[11px] text-text-disabled">{relativeTime(conversation.last_message_at)}</span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-text-secondary">{conversation.last_message_preview ?? "No messages yet"}</p>
                  <div className="mt-2 flex min-h-5 items-center gap-1.5 overflow-hidden">
                    <span className="inline-flex shrink-0 items-center gap-1 text-[10px] font-medium text-text-disabled">
                      <span className={`h-1.5 w-1.5 rounded-full ${conversation.status === "open" ? "bg-success" : "bg-text-disabled"}`} />
                      {STATUS_LABELS[conversation.status as ConversationStatus] ?? conversation.status}
                    </span>
                    {conversation.window.is_open ? (
                      <span title="WhatsApp service window is open" className="inline-flex shrink-0 items-center gap-1 text-[10px] font-medium text-success">
                        <MessageCircle aria-hidden className="h-3 w-3" /> Window open
                      </span>
                    ) : null}
                    {signal ? (
                      <span title="Response indicator derived from unread wait time; not a server policy" className={`inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${signal.className}`}>
                        <Clock3 aria-hidden className="h-3 w-3" /> {signal.label}
                      </span>
                    ) : null}
                    {conversation.tags.slice(0, 1).map((tag) => <TagChip key={tag.id} name={tag.name} color={tag.color} />)}
                    {conversation.tags.length > 1 ? <span className="shrink-0 text-[10px] font-semibold text-text-disabled">+{conversation.tags.length - 1}</span> : null}
                    {conversation.unread_count > 0 ? <span className="ml-auto shrink-0 rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-bold text-accent-fg">{conversation.unread_count}</span> : null}
                  </div>
                </div>
              </div>
            </button>
            <button
              type="button"
              aria-label={pinned ? "Unpin conversation" : "Pin conversation"}
              aria-pressed={pinned}
              onClick={() => onTogglePinned(conversation.id)}
              className={`absolute right-2 top-8 rounded-md p-1.5 transition-opacity hover:bg-hover focus:opacity-100 ${pinned ? "text-accent" : "text-text-disabled opacity-0 group-hover:opacity-100"}`}
            >
              {pinned ? <PinOff aria-hidden className="h-3.5 w-3.5" /> : <Pin aria-hidden className="h-3.5 w-3.5" />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
