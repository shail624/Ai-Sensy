import { useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "@/components/ui";
import {
  apiErrorMessage,
  useDefaultPhoneNumber,
  useQuickReplies,
  useSendMessage,
} from "@/features/inbox/api";
import type { Conversation } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";

interface Props {
  conversation: Conversation;
}

/**
 * Outbound text composer with quick-reply insertion (FR-INB-04). Sending is gated on
 * `messages:send`; outside the 24-hour service window the API rejects free-form text, so the
 * composer says so rather than letting the user compose into a guaranteed failure.
 */
export function MessageComposer({ conversation }: Props): JSX.Element {
  const [body, setBody] = useState("");
  const [showReplies, setShowReplies] = useState(false);
  const canSend = useHasPermission("messages:send");
  const canManageQuickReplies = useHasPermission("inbox:write");
  const quickReplies = useQuickReplies();
  const phoneNumber = useDefaultPhoneNumber();
  const send = useSendMessage(conversation.id);

  const windowOpen = conversation.window.is_open;
  const to = conversation.contact?.phone ?? "";
  const numberId = phoneNumber.data?.id ?? "";
  const disabled = !canSend || !windowOpen || !to || !numberId || send.isPending;

  function submit(): void {
    if (!body.trim() || disabled) return;
    send.mutate(
      { phoneNumberId: numberId, to, body: body.trim() },
      { onSuccess: () => setBody("") },
    );
  }

  if (!canSend) {
    return (
      <p className="border-t border-border p-3 text-xs text-text-disabled">
        You do not have permission to send messages in this conversation.
      </p>
    );
  }

  return (
    <div className="border-t border-border p-3">
      {!windowOpen ? (
        <p className="mb-2 text-xs text-warning">
          The 24-hour service window is closed. Reply with an approved template to reopen it.
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
        onChange={(event) => setBody(event.target.value)}
        onKeyDown={(event) => {
          // Enter sends; Shift+Enter inserts a newline.
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={windowOpen ? "Write a reply…" : "Window closed"}
        className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary disabled:opacity-50"
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
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
        >
          Quick replies
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !body.trim()}
          className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
        >
          {send.isPending ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}
