import { ChevronLeft, ChevronRight, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useRef } from "react";

import { ApiStatus } from "@/components/layout/ApiStatus";
import { AlertToggle } from "@/features/inbox/AlertToggle";
import { CustomerAvatar } from "@/features/inbox/CustomerAvatar";
import type { Conversation } from "@/features/inbox/types";

function label(conversation: Conversation): string {
  return conversation.contact?.name ?? conversation.contact?.phone ?? "Unknown";
}

interface Props {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  listCollapsed: boolean;
  onToggleList: () => void;
}

/**
 * The strip above the thread: every chat with unread messages as an avatar with its count, so an
 * agent can jump between waiting customers without scanning the list. Arrows scroll the strip.
 */
export function ChatQuickSwitcher({ conversations, selectedId, onSelect, listCollapsed, onToggleList }: Props): JSX.Element {
  const stripRef = useRef<HTMLUListElement>(null);
  const waiting = conversations.filter((conversation) => conversation.unread_count > 0);

  function scroll(direction: -1 | 1): void {
    stripRef.current?.scrollBy({ left: direction * 240, behavior: "smooth" });
  }

  const arrow =
    "flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-black/55 transition-colors duration-150 hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-text-secondary";

  return (
    <div className="hidden h-[60px] shrink-0 items-center bg-[#fdfffc] dark:bg-surface lg:flex">
      <button
        type="button"
        onClick={onToggleList}
        aria-label={listCollapsed ? "Expand conversation list" : "Collapse conversation list"}
        title={listCollapsed ? "Expand conversation list" : "Collapse conversation list"}
        className={arrow}
      >
        {listCollapsed ? <PanelLeftOpen aria-hidden className="h-5 w-5" /> : <PanelLeftClose aria-hidden className="h-5 w-5" />}
      </button>
      {waiting.length > 0 ? (
        <button type="button" aria-label="Scroll waiting chats left" onClick={() => scroll(-1)} className={arrow}>
          <ChevronLeft aria-hidden className="h-6 w-6" />
        </button>
      ) : null}
      <ul ref={stripRef} aria-label="Chats waiting for a reply" className="flex min-w-0 flex-1 items-center gap-4 overflow-x-auto px-2 [scrollbar-width:none]">
        {waiting.map((conversation) => {
          const name = label(conversation);
          const selected = conversation.id === selectedId;
          return (
            <li key={conversation.id} className="shrink-0">
              <button
                type="button"
                onClick={() => onSelect(conversation.id)}
                aria-label={`${name}, ${conversation.unread_count} unread`}
                title={name}
                className="group relative flex w-10 flex-col items-center rounded-xl pt-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                <CustomerAvatar
                  conversation={conversation}
                  className={`h-10 w-10 bg-[#f5efdf] text-xl text-[#0a474c] transition-transform duration-150 group-hover:scale-105 ${selected ? "ring-2 ring-[var(--color-nav-bg)]" : ""}`}
                />
                <span className="absolute -right-2 -top-0 flex h-5 min-w-5 items-center justify-center rounded-full bg-[var(--color-nav-bg)] px-1 text-[10px] text-white">
                  {conversation.unread_count > 99 ? "99+" : conversation.unread_count}
                </span>
                <span className="mt-0.5 max-w-[64px] truncate text-[10px] leading-[11px] text-black dark:text-text-primary">
                  {name.split(/\s+/)[0]}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {waiting.length > 0 ? (
        <button type="button" aria-label="Scroll waiting chats right" onClick={() => scroll(1)} className={arrow}>
          <ChevronRight aria-hidden className="h-6 w-6" />
        </button>
      ) : null}
      <ApiStatus className="ml-auto" />
      <span className="pr-3"><AlertToggle /></span>
    </div>
  );
}
