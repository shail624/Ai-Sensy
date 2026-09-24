import { QrCode, ShieldCheck } from "lucide-react";

import type { Conversation } from "@/features/inbox/types";
import { connectorLabel, isWahaConversation } from "@/features/inbox/types";

/**
 * A bold "API" or "QR" pill so agents see at a glance which WhatsApp a chat came through:
 * green shield for the official WhatsApp Business API, blue QR code for the QR-scanned phone.
 */
export function ChannelBadge({ conversation, onDark = false }: { conversation: Pick<Conversation, "connector_type">; onDark?: boolean }): JSX.Element {
  const qr = isWahaConversation(conversation as Conversation);
  const colours = qr
    ? onDark ? "bg-[#dbeafe] text-[#1d4ed8]" : "bg-[#dbeafe] text-[#1d4ed8] ring-1 ring-[#93c5fd]"
    : onDark ? "bg-[#dcfce7] text-[#15803d]" : "bg-[#dcfce7] text-[#15803d] ring-1 ring-[#86efac]";
  return (
    <span
      title={connectorLabel(conversation as Conversation)}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${colours}`}
    >
      {qr ? <QrCode aria-hidden className="h-3.5 w-3.5" strokeWidth={2.5} /> : <ShieldCheck aria-hidden className="h-3.5 w-3.5" strokeWidth={2.5} />}
      {qr ? "QR" : "API"}
      <span className="sr-only">{connectorLabel(conversation as Conversation)}</span>
    </span>
  );
}
