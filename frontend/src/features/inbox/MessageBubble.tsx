import { AlertCircle, Check, CheckCheck, Clock3 } from "lucide-react";
import { useState, type ReactNode } from "react";

import {
  readInteractive,
  readLocation,
  readMedia,
  readTemplate,
  readText,
  type ReactionContent,
} from "@/features/inbox/messageContent";
import { MessageMedia } from "@/features/inbox/MessageMedia";
import type { Message } from "@/features/inbox/types";
import { REACTION_EMOJI } from "@/features/inbox/types";

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
    // A link-only attachment (e.g. a URL sent through the API) has no stored file to show.
    if (media.link) {
      return (
        <div>
          <a href={media.link} target="_blank" rel="noreferrer noopener" className="font-medium underline-offset-2 hover:underline">
            📎 {media.filename ?? "Open attachment"}
          </a>
          {media.caption ? <p className="mt-1 whitespace-pre-wrap">{media.caption}</p> : null}
        </div>
      );
    }
    return (
      <div className="space-y-1">
        <MessageMedia messageId={message.id} media={media} />
        {media.caption ? (
          <p className={`whitespace-pre-wrap ${media.kind === "image" || media.kind === "video" ? "px-2 pb-1" : ""}`}>{media.caption}</p>
        ) : null}
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
    const hasPin = location.latitude !== undefined && location.longitude !== undefined;
    return (
      <div>
        <p className="flex items-center gap-1.5 font-medium">
          <span aria-hidden>📍</span>
          <span>{location.name ?? (hasPin ? `${location.latitude}, ${location.longitude}` : "Location")}</span>
        </p>
        {hasPin ? (
          <a
            href={`https://www.google.com/maps?q=${location.latitude},${location.longitude}`}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-0.5 inline-block text-xs underline underline-offset-2"
          >
            Open in Google Maps
          </a>
        ) : null}
      </div>
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
  /** The customer's avatar, shown beside inbound messages. */
  customerAvatar?: ReactNode;
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
export function MessageBubble({ message, onReact, canReact, reactions = [], customerAvatar }: Props): JSX.Element {
  const [pickerOpen, setPickerOpen] = useState(false);
  const outbound = message.direction === "outbound";
  const template = Boolean(readTemplate(message));
  // Photos and videos sit edge to edge in a thin frame, as on WhatsApp; stickers have no bubble.
  const media = readMedia(message);
  const pictureKind = media && !media.link ? media.kind : null;
  const sticker = pictureKind === "sticker";
  const picture = pictureKind === "image" || pictureKind === "video";

  return (
    <li className={`group flex items-start gap-2 ${outbound ? "flex-row-reverse" : ""}`}>
      {outbound || !customerAvatar ? (
        <span
          aria-hidden
          className={`mt-px flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full text-sm ${
            outbound ? "border border-[var(--color-nav-bg)] bg-[#f0f0f0] text-black" : "bg-[#ffa500] text-black"
          }`}
        >
          {outbound ? "A" : null}
        </span>
      ) : (
        <span className="mt-px">{customerAvatar}</span>
      )}
      <div className={`flex max-w-[400px] flex-col ${outbound ? "items-end" : "items-start"}`}>
        <div
          className={`text-sm leading-[19px] ${
            sticker ? "" : picture ? "overflow-hidden rounded-[14px] p-[3px]" : "rounded-[22px] px-4 py-2"
          } ${
            sticker
              ? ""
              : outbound
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
