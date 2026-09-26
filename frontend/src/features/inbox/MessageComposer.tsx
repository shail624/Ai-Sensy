import {
  FileText,
  Image as ImageIcon,
  MapPin,
  Music,
  Paperclip,
  Smile,
} from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "@/components/ui";
import {
  apiErrorMessage,
  useQuickReplies,
  useSendAttachment,
  useSendMessage,
  useTypingSignal,
  type AttachmentKind,
} from "@/features/inbox/api";
import {
  ACCEPT,
  AttachmentPreview,
  classifyFile,
} from "@/features/inbox/AttachmentPreview";
import { EmojiPicker } from "@/features/inbox/EmojiPicker";
import { LocationDialog } from "@/features/inbox/LocationDialog";
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
  const sendAttachment = useSendAttachment(conversation.id);
  const [attachment, setAttachment] = useState<{
    file: File;
    kind: AttachmentKind;
  } | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [panel, setPanel] = useState<"emoji" | "attach" | null>(null);
  const [locationOpen, setLocationOpen] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const isWaha = isWahaConversation(conversation);
  const qrStatus = useWhatsAppQrStatus(isWaha);

  const to = conversation.contact?.phone ?? "";
  const metaWindowClosed = !isWaha && !conversation.window.is_open;
  const wahaStatusUnknown = isWaha && qrStatus.isLoading;
  const wahaNotConnected =
    isWaha && !qrStatus.isLoading && qrStatus.data?.connected !== true;
  const refused = metaWindowClosed || wahaNotConnected || wahaStatusUnknown;
  const busy = send.isPending || sendAttachment.isPending;
  const disabled = !canSend || !to || busy || refused;
  // Typing indicators are a Meta Cloud API feature; the server applies the workspace policy.
  const signalTyping = useTypingSignal(conversation.id, !isWaha && !disabled);

  function submit(): void {
    if (disabled) return;
    if (attachment) {
      // The typed text travels as the file's caption, as on WhatsApp.
      sendAttachment.mutate(
        { file: attachment.file, kind: attachment.kind, caption: body },
        {
          onSuccess: () => {
            setAttachment(null);
            setBody("");
          },
        },
      );
      return;
    }
    if (!body.trim()) return;
    send.mutate({ body: body.trim() }, { onSuccess: () => setBody("") });
  }

  function insertEmoji(emoji: string): void {
    const field = textRef.current;
    const start = field?.selectionStart ?? body.length;
    const end = field?.selectionEnd ?? body.length;
    const next = body.slice(0, start) + emoji + body.slice(end);
    setBody(next);
    requestAnimationFrame(() => {
      field?.focus();
      field?.setSelectionRange(start + emoji.length, start + emoji.length);
    });
  }

  function chooseFile(accept: string): void {
    setPanel(null);
    if (!fileRef.current) return;
    fileRef.current.accept = accept;
    fileRef.current.value = "";
    fileRef.current.click();
  }

  function onFileChosen(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    if (!file) return;
    const result = classifyFile(file);
    if ("error" in result) {
      setAttachError(result.error);
      setAttachment(null);
      return;
    }
    setAttachError(null);
    sendAttachment.reset();
    setAttachment({ file, kind: result.kind });
    textRef.current?.focus();
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
          The 24-hour service window is closed. Reply with an approved template
          to reopen it.
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
                <Link
                  to="/settings/canned-messages"
                  className="text-accent hover:underline"
                >
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
                    <span className="font-medium text-text-primary">
                      {reply.shortcut}
                    </span>{" "}
                    <span className="text-text-secondary">{reply.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {attachment ? (
        <AttachmentPreview
          file={attachment.file}
          kind={attachment.kind}
          onRemove={() => setAttachment(null)}
        />
      ) : null}
      {attachError ? (
        <p role="alert" className="mb-2 text-xs text-danger">
          {attachError}
        </p>
      ) : null}
      <input
        ref={fileRef}
        type="file"
        className="hidden"
        aria-label="Choose a file"
        onChange={onFileChosen}
      />

      <label htmlFor="composer-body" className="sr-only">
        Message
      </label>
      <textarea
        id="composer-body"
        ref={textRef}
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
        placeholder={
          attachment && !refused ? "Add a caption (optional)…" : placeholder
        }
        className="w-full rounded-[20px] border-0 bg-surface px-4 py-2 text-sm text-text-primary shadow-[0_1px_2px_rgba(0,0,0,0.06)] placeholder:text-[#9e9e9e] focus:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50"
      />

      {send.error || sendAttachment.error ? (
        <div className="mt-2">
          <ErrorState
            message={apiErrorMessage(send.error ?? sendAttachment.error)}
          />
        </div>
      ) : null}

      <div className="relative mt-2 flex items-center justify-between gap-2">
        {panel === "emoji" ? (
          <div className="absolute bottom-11 left-0 z-20">
            <EmojiPicker onPick={insertEmoji} />
          </div>
        ) : null}
        {panel === "attach" ? (
          <div
            role="menu"
            aria-label="Attach"
            className="absolute bottom-11 left-10 z-20 w-56 rounded-lg border border-border bg-surface p-1 shadow-card"
          >
            {(
              [
                ["Photos & videos", ACCEPT.media, ImageIcon, "text-[#7c3aed]"],
                ["Document", ACCEPT.document, FileText, "text-[#2563eb]"],
                ["Audio / music", ACCEPT.audio, Music, "text-[#ea580c]"],
              ] as const
            ).map(([label, accept, Icon, colour]) => (
              <button
                key={label}
                type="button"
                role="menuitem"
                onClick={() => chooseFile(accept)}
                className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-text-primary hover:bg-hover"
              >
                <Icon aria-hidden className={`h-5 w-5 ${colour}`} /> {label}
              </button>
            ))}
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setPanel(null);
                setLocationOpen(true);
              }}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-text-primary hover:bg-hover"
            >
              <MapPin aria-hidden className="h-5 w-5 text-[#16a34a]" /> Location
            </button>
          </div>
        ) : null}
        {locationOpen ? <LocationDialog conversationId={conversation.id} onClose={() => setLocationOpen(false)} /> : null}
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Emoji"
            title="Emoji"
            aria-expanded={panel === "emoji"}
            disabled={disabled}
            onClick={() =>
              setPanel((open) => (open === "emoji" ? null : "emoji"))
            }
            className="flex h-9 w-9 items-center justify-center rounded-full text-black/55 transition-colors hover:bg-black/5 disabled:opacity-50 dark:text-text-secondary"
          >
            <Smile aria-hidden className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Attach a file"
            title="Attach a file"
            aria-expanded={panel === "attach"}
            disabled={disabled}
            onClick={() =>
              setPanel((open) => (open === "attach" ? null : "attach"))
            }
            className="flex h-9 w-9 items-center justify-center rounded-full text-black/55 transition-colors hover:bg-black/5 disabled:opacity-50 dark:text-text-secondary"
          >
            <Paperclip aria-hidden className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={() => setShowReplies((open) => !open)}
            aria-expanded={showReplies}
            className="h-9 rounded-full border border-[rgba(10,71,76,0.5)] px-4 text-sm font-medium text-[var(--color-nav-bg)] transition-colors hover:bg-[#ebf5f3] dark:text-accent"
          >
            Quick replies
          </button>
        </div>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || (!attachment && !body.trim())}
          className="h-9 rounded-full bg-[var(--color-nav-bg)] px-5 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-50"
        >
          {sendAttachment.isPending
            ? "Uploading…"
            : send.isPending
              ? "Sending…"
              : "Send"}
        </button>
      </div>
    </div>
  );
}
