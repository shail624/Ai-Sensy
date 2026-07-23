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

interface Props {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** The inbox rail: one row per conversation, newest activity first. */
export function ConversationList({ conversations, selectedId, onSelect }: Props): JSX.Element {
  return (
    <ul className="divide-y divide-border" aria-label="Conversations">
      {conversations.map((conversation) => {
        const selected = conversation.id === selectedId;
        return (
          <li key={conversation.id}>
            <button
              type="button"
              onClick={() => onSelect(conversation.id)}
              aria-current={selected ? "true" : undefined}
              className={`w-full px-3 py-2 text-left hover:bg-hover ${
                selected ? "bg-surface-2" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="truncate text-sm font-medium text-text-primary">
                  {displayName(conversation)}
                </span>
                <span className="shrink-0 text-xs text-text-disabled">
                  {relativeTime(conversation.last_message_at)}
                </span>
              </div>

              <p className="mt-0.5 truncate text-xs text-text-secondary">
                {conversation.last_message_preview ?? "No messages yet"}
              </p>

              <div className="mt-1 flex flex-wrap items-center gap-1">
                <span className="rounded-full border border-border px-2 py-0.5 text-xs text-text-secondary">
                  {STATUS_LABELS[conversation.status as ConversationStatus] ?? conversation.status}
                </span>
                {conversation.window.is_open ? (
                  <span className="rounded-full border border-success px-2 py-0.5 text-xs text-success">
                    Window open
                  </span>
                ) : null}
                {conversation.unread_count > 0 ? (
                  <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-accent-fg">
                    {conversation.unread_count}
                  </span>
                ) : null}
                {conversation.tags.map((tag) => (
                  <TagChip key={tag.id} name={tag.name} color={tag.color} />
                ))}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
