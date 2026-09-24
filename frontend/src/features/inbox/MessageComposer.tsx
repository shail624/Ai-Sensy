import { useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "@/components/ui";
import { apiErrorMessage, useQuickReplies, useSendMessage, useTypingSignal } from "@/features/inbox/api";
import type { Conversation } from "@/features/inbox/types";
import { isWahaConversation } from "@/features/inbox/types";
import { useWhatsAppQrStatus } from "@/features/whatsapp-qr/api";
import { useHasPermission } from "@/lib/auth";

interface Props {
  conversation: Conversation;
}

/**
 * Outbound text composer with quick-reply insertion (FR-INB-04). Sending is gated on
 * `messages:send`; who actually receives the send — which provider, which endpoint — is a
 * decision the server makes from the conversation's own durable ownership (QR-08), never a value
 * this component sends.
 *
 * The two providers refuse to send for different, provider-true reasons: outside Meta's 24-hour
 * service window the API rejects free-form text (FR-WA-12); a WAHA thread carries no such window,
 * but genuinely refuses when the underlying session is not currently connected — read here from
 * QR-07's own live status (a passive read, the same one the Channels page polls; opening this
 * conversation never triggers a reconnect or pairing attempt on its own).
 */
export function MessageComposer({ conversation }: Props): JSX.Element {
  const [body, setBody] = useState("");
  const [showReplies, setShowReplies] = useState(false);
  const canSend = useHasPermission("messages:send");
  const canManageQuickReplies = useHasPermission("inbox:write");
  const quickReplies = useQuickReplies();
  const send = useSendMessage(conversation.id);

  const isWaha = isWahaConversation(conversation);
  const qrStatus = useWhatsAppQrStatus(isWaha);

  const to = conversation.contact?.phone ?? "";
  const metaWindowClosed = !isWaha && !conversation.window.is_open;
  const wahaStatusUnknown = isWaha && qrStatus.isLoading;
  const wahaNotConnected = isWaha && !qrStatus.isLoading && qrStatus.data?.connected !== true;
  const refused = metaWindowClosed || wahaNotConnected || wahaStatusUnknown;
  const disabled = !canSend || !to || send.isPending || refused;
  // Typing indicators are a Meta Cloud API feature; the server applies the workspace policy.
  const signalTyping = useTypingSignal(conversation.id, !isWaha && !disabled);

  function submit(): void {
    if (!body.trim() || disabled) return;
    send.mutate({ body: body.trim() }, { onSuccess: () => setBody("") });
  }

  if (!canSend) {
    return (
      <p className="bg-[#f5f5f5] px-4 py-[13px] text-center text-xs text-text-secondary dark:bg-surface">
        You do not have permission to send messages in this conversation.
      </p>
    );
  }

  const placeholder = metaWindowClosed
    ? "Window closed"
    : wahaStatusUnknown
      ? "Checking connection…"
      : wahaNotConnected
        ? "WhatsApp not connected"
        : "Write a reply…";

  return (
    <div className="bg-[#f5f5f5] px-4 py-3 dark:bg-surface">
      {metaWindowClosed ? (
        <p className="mb-2 text-xs text-warning">
          The 24-hour service window is closed. Reply with an approved template to reopen it.
        </p>
      ) : null}
      {wahaNotConnected ? (
        <p className="mb-2 text-xs text-danger">
          {qrStatus.data?.health_detail ??
            "WhatsApp is not currently connected. Reconnect it from Settings → WhatsApp before sending."}
        </p>
      ) : null}

      {showReplies ? (
        <div className="mb-2 max-h-40 overflow-y-auto rounded-md border border-border">
          {(quickReplies.data ?? []).length === 0 ? (
            <div className="px-2 py-1.5 text-xs text-text-disabled">
              <p>No quick replies yet.</p>
              {canManageQuickReplies ? (
                <Link to="/settings/canned-messages" className="text-accent hover:underline">
                  Create one in Settings → Canned Messages
                </Link>
              ) : null}
            </div>
          ) : (
            <ul>
              {(quickReplies.data ?? []).map((reply) => (
                <li key={reply.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setBody(reply.body);
                      setShowReplies(false);
                    }}
                    className="block w-full px-2 py-1.5 text-left text-sm hover:bg-hover"
                  >
                    <span className="font-medium text-text-primary">{reply.shortcut}</span>{" "}
                    <span className="text-text-secondary">{reply.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      <label htmlFor="composer-body" className="sr-only">
        Message
      </label>
      <textarea
        id="composer-body"
        rows={2}
        value={body}
        disabled={disabled}
        onChange={(event) => {
          setBody(event.target.value);
          if (event.target.value.trim()) signalTyping();
        }}
        onKeyDown={(event) => {
          // Enter sends; Shift+Enter inserts a newline.
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={placeholder}
        className="w-full rounded-[20px] border-0 bg-surface px-4 py-2 text-sm text-text-primary shadow-[0_1px_2px_rgba(0,0,0,0.06)] placeholder:text-[#9e9e9e] focus:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50"
      />

      {send.error ? (
        <div className="mt-2">
          <ErrorState message={apiErrorMessage(send.error)} />
        </div>
      ) : null}

      <div className="mt-2 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setShowReplies((open) => !open)}
          aria-expanded={showReplies}
          className="h-9 rounded-full border border-[rgba(10,71,76,0.5)] px-4 text-sm font-medium text-[var(--color-nav-bg)] transition-colors hover:bg-[#ebf5f3] dark:text-accent"
        >
          Quick replies
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !body.trim()}
          className="h-9 rounded-full bg-[var(--color-nav-bg)] px-5 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-50"
        >
          {send.isPending ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}
