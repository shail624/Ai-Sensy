import { UserRound } from "lucide-react";

import { useConversationPhoto } from "@/features/inbox/api";
import type { Conversation } from "@/features/inbox/types";

/** The first letter of a real name; `null` when there is only a phone number to show. */
export function nameInitial(conversation: Pick<Conversation, "contact">): string | null {
  const name = conversation.contact?.name?.trim();
  const first = name?.match(/\p{L}/u)?.[0];
  return first ? first.toUpperCase() : null;
}

interface Props {
  conversation: Pick<Conversation, "id" | "contact" | "connector_type">;
  /** Tailwind size + background classes, e.g. "h-10 w-10 bg-[#f5efdf] text-xl". */
  className: string;
  iconClassName?: string;
}

/**
 * The customer's WhatsApp profile photo when WhatsApp shares one, otherwise the
 * first letter of their name, otherwise a person icon — never a stray "+" from a phone number.
 */
export function CustomerAvatar({ conversation, className, iconClassName = "h-1/2 w-1/2" }: Props): JSX.Element {
  // Looked up through the QR WhatsApp for every chat: Meta's API shares no profile photos.
  const photo = useConversationPhoto(conversation.id, true);
  const initial = nameInitial(conversation);
  return (
    <span aria-hidden className={`flex shrink-0 items-center justify-center overflow-hidden rounded-full ${className}`}>
      {photo ? (
        <img src={photo} alt="" className="h-full w-full object-cover" />
      ) : initial ? (
        initial
      ) : (
        <UserRound className={iconClassName} />
      )}
    </span>
  );
}
