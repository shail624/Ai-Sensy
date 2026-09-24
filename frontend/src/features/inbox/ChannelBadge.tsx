import { QrCode, ShieldCheck } from "lucide-react";

import type { Conversation } from "@/features/inbox/types";
import { connectorLabel, isWahaConversation } from "@/features/inbox/types";

/**
 * A bold "API" or "QR" pill so agents see at a glance which WhatsApp a chat came through:
 * green shield for the official WhatsApp Business API, blue QR code for the QR-scanned phone.
 */
export function ChannelBadge({ conversation, onDark = false }: { conversation: Pick<Conversation, "connector_type">; onDark?: boolean }): JSX.Element {
  const qr = isWahaConversation(conversation as Conversation);
  // Kept quiet on purpose (owner feedback): a small tinted label, not a highlighted pill.
  const colours = onDark
    ? "bg-white/15 text-white"
    : qr
      ? "bg-[#eff6ff] text-[#3b6fd8]"
      : "bg-[#f0fdf4] text-[#2f8a4f]";
  return (
    <span
      title={connectorLabel(conversation as Conversation)}
      className={`inline-flex shrink-0 items-center gap-0.5 rounded px-1 text-[9px] font-semibold uppercase leading-[14px] ${colours}`}
    >
      {qr ? <QrCode aria-hidden className="h-2.5 w-2.5" /> : <ShieldCheck aria-hidden className="h-2.5 w-2.5" />}
      {qr ? "QR" : "API"}
      <span className="sr-only">{connectorLabel(conversation as Conversation)}</span>
    </span>
  );
}
