import { AlertCircle, Check, CheckCheck, Clock3 } from "lucide-react";
import { useState } from "react";

import {
  readInteractive,
  readLocation,
  readMedia,
  readTemplate,
  readText,
  type ReactionContent,
} from "@/features/inbox/messageContent";
import type { Message } from "@/features/inbox/types";
import { REACTION_EMOJI } from "@/features/inbox/types";

const MEDIA_GLYPH: Record<string, string> = {
  image: "🖼",
  video: "🎬",
  audio: "🎧",
  document: "📄",
  sticker: "🏷",
};

/** Outbound delivery state, shown as a compact receipt (Doc 07 ledger states). */
function receipt(message: Message): string {
  if (message.status === "failed") return "Failed";
  if (message.read_at) return "Read";
  if (message.delivered_at) return "Delivered";
  if (message.sent_at) return "Sent";
  return "Queued";
}

/** Render whichever canonical payload this message carries (text · media · template · …). */
function MessageBody({ message }: { message: Message }): JSX.Element {
  const media = readMedia(message);
  if (media) {
    const glyph = MEDIA_GLYPH[media.kind] ?? "📎";
    return (
      <div>
        <p className="flex items-center gap-1.5 font-medium">
          <span aria-hidden>{glyph}</span>
          <span>{media.filename ?? media.kind}</span>
        </p>
        {media.mimeType ? (
          <p className="mt-0.5 text-xs opacity-75">{media.mimeType}</p>
        ) : null}
        {media.link ? (
          <a
            href={media.link}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-0.5 inline-block text-xs underline-offset-2 hover:underline"
          >
            Open attachment
          </a>
        ) : null}
        {media.caption ? <p className="mt-1 whitespace-pre-wrap">{media.caption}</p> : null}
      </div>
    );
  }

  const template = readTemplate(message);
  if (template) {
    return (
      <div>
        <p className="flex items-center gap-1.5 font-medium">
          <span aria-hidden>📋</span>
          <span>Template: {template.name}</span>
        </p>
        {template.language ? (
          <p className="mt-0.5 text-xs opacity-75">{template.language}</p>
        ) : null}
      </div>
    );
  }

  const location = readLocation(message);
  if (location) {
    return (
      <p className="flex items-center gap-1.5">
        <span aria-hidden>📍</span>
        <span>
          {location.name ??
            (location.latitude !== undefined
              ? `${location.latitude}, ${location.longitude}`
              : "Location")}
        </span>
      </p>
    );
  }

  const interactive = readInteractive(message);
  if (interactive) {
    return (
      <p className="flex items-center gap-1.5">
        <span aria-hidden>☑</span>
        <span>{interactive}</span>
      </p>
    );
  }

  const text = readText(message.content as Record<string, unknown> | null);
  if (text) return <p className="whitespace-pre-wrap break-words">{text}</p>;

  // An unmapped type is still a real message — name it rather than render an empty bubble.
  return <p className="italic opacity-75">[{message.message_type}]</p>;
}

interface Props {
  message: Message;
  onReact: (emoji: string) => void;
  canReact: boolean;
  reactions?: ReactionContent[];
  /** First letter of the customer's name, for the inbound avatar. */
  contactInitial?: string;
}

function ReceiptIcon({ message }: { message: Message }): JSX.Element {
  const state = receipt(message);
  if (state === "Failed") return <AlertCircle aria-hidden className="h-[15px] w-[15px] text-danger" />;
  if (state === "Queued") return <Clock3 aria-hidden className="h-[13px] w-[13px] text-[#808080]" />;
  if (state === "Sent") return <Check aria-hidden className="h-[15px] w-[15px] text-[#808080]" />;
  return <CheckCheck aria-hidden className={`h-[15px] w-[15px] ${state === "Read" ? "text-[#08cf65]" : "text-[#808080]"}`} />;
}

/**
 * The reference chat bubble: customer messages in solid teal on the left beside an orange initial,
 * team messages in white on the right; 22px corners, 10px time and a tick receipt underneath.
 */
export function MessageBubble({ message, onReact, canReact, reactions = [], contactInitial = "?" }: Props): JSX.Element {
  const [pickerOpen, setPickerOpen] = useState(false);
  const outbound = message.direction === "outbound";
  const template = Boolean(readTemplate(message));

  return (
    <li className={`group flex items-start gap-2 ${outbound ? "flex-row-reverse" : ""}`}>
      <span
        aria-hidden
        className={`mt-px flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full text-sm ${
          outbound ? "border border-[var(--color-nav-bg)] bg-[#f0f0f0] text-black" : "bg-[#ffa500] text-black"
        }`}
      >
        {outbound ? "A" : contactInitial}
      </span>
      <div className={`flex max-w-[400px] flex-col ${outbound ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-[22px] px-4 py-2 text-sm leading-[19px] ${
            outbound
              ? template
                ? "bg-[#fbf9f3] text-[#0a474c] dark:bg-surface dark:text-text-primary"
                : "bg-white text-[#484848] dark:bg-surface dark:text-text-primary"
              : "bg-[#0a474c] text-white"
          }`}
        >
          <MessageBody message={message} />
        </div>

        {reactions.length > 0 ? (
          <ul aria-label="Reactions" className="-mt-1.5 flex gap-1 px-2">
            {reactions.map((reaction, index) => (
              <li key={`${reaction.emoji}-${index}`} className="rounded-full bg-surface px-1.5 py-0.5 text-xs shadow-sm">
                {reaction.emoji}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex items-center gap-1 p-1 text-[10px] text-black dark:text-text-secondary">
          <span>{new Date(message.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</span>
          {outbound ? (
            <>
              <ReceiptIcon message={message} />
              <span className="sr-only">{receipt(message)}</span>
            </>
          ) : null}
          {message.error_code ? <span className="text-danger">{message.error_code}</span> : null}
          {canReact ? (
            <button
              type="button"
              aria-label={`React to message ${message.id}`}
              aria-expanded={pickerOpen}
              onClick={() => setPickerOpen((open) => !open)}
              className="rounded px-1 text-sm opacity-0 transition-opacity hover:bg-black/5 focus:opacity-100 group-hover:opacity-100"
            >
              ☺
            </button>
          ) : null}
        </div>

        {pickerOpen ? (
          <div role="group" aria-label="Choose a reaction" className="flex gap-1 rounded-full bg-surface p-1 shadow-md">
            {REACTION_EMOJI.map((emoji) => (
              <button
                key={emoji}
                type="button"
                aria-label={`React ${emoji}`}
                onClick={() => {
                  onReact(emoji);
                  setPickerOpen(false);
                }}
                className="rounded-full px-1.5 py-0.5 text-sm transition-transform hover:scale-125 hover:bg-hover"
              >
                {emoji}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </li>
  );
}
