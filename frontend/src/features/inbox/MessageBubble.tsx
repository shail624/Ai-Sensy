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
          <p className="mt-0.5 text-xs text-text-secondary">{media.mimeType}</p>
        ) : null}
        {media.link ? (
          <a
            href={media.link}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-0.5 inline-block text-xs text-accent hover:underline"
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
          <p className="mt-0.5 text-xs text-text-secondary">{template.language}</p>
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
  return <p className="italic text-text-secondary">[{message.message_type}]</p>;
}

interface Props {
  message: Message;
  onReact: (emoji: string) => void;
  canReact: boolean;
  reactions?: ReactionContent[];
}

export function MessageBubble({ message, onReact, canReact, reactions = [] }: Props): JSX.Element {
  const [pickerOpen, setPickerOpen] = useState(false);
  const outbound = message.direction === "outbound";

  return (
    <li className={`flex ${outbound ? "justify-end" : "justify-start"}`}>
      <div className="max-w-[80%]">
        <div
          className={`rounded-lg border px-3 py-2 text-sm ${
            outbound
              ? "border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] bg-surface-2 text-text-primary"
              : "border-border bg-surface text-text-primary"
          }`}
        >
          <MessageBody message={message} />
        </div>

        {reactions.length > 0 ? (
          <ul
            aria-label="Reactions"
            className={`mt-1 flex gap-1 ${outbound ? "justify-end" : "justify-start"}`}
          >
            {reactions.map((reaction, index) => (
              <li
                key={`${reaction.emoji}-${index}`}
                className="rounded-full border border-border bg-surface-2 px-1.5 py-0.5 text-xs"
              >
                {reaction.emoji}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-0.5 flex items-center gap-2 text-xs text-text-disabled">
          <span>{new Date(message.created_at).toLocaleTimeString()}</span>
          {outbound ? <span>{receipt(message)}</span> : null}
          {message.error_code ? <span className="text-danger">{message.error_code}</span> : null}
          {canReact ? (
            <button
              type="button"
              aria-label={`React to message ${message.id}`}
              aria-expanded={pickerOpen}
              onClick={() => setPickerOpen((open) => !open)}
              className="rounded px-1 hover:bg-hover"
            >
              ☺
            </button>
          ) : null}
        </div>

        {pickerOpen ? (
          <div role="group" aria-label="Choose a reaction" className="mt-1 flex gap-1">
            {REACTION_EMOJI.map((emoji) => (
              <button
                key={emoji}
                type="button"
                aria-label={`React ${emoji}`}
                onClick={() => {
                  onReact(emoji);
                  setPickerOpen(false);
                }}
                className="rounded border border-border px-1.5 py-0.5 text-sm hover:bg-hover"
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
