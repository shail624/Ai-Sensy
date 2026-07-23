import type { Message } from "@/features/inbox/types";

/**
 * Readers for the canonical `content_json` shapes the channel layer normalises every message into
 * (Doc 07 §5.2). The payload is an untyped object in the contract, so these are the single place
 * that knows its shape — components stay declarative.
 */
type Content = Record<string, unknown> | null;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

export interface MediaContent {
  kind: string;
  caption: string | null;
  filename: string | null;
  mimeType: string | null;
  link: string | null;
}

export interface TemplateContent {
  name: string;
  language: string | null;
}

export interface ReactionContent {
  /** The wamid of the message being reacted to. */
  targetWamid: string | null;
  emoji: string;
}

export function isReaction(message: Message): boolean {
  return message.message_type === "reaction" || Boolean(asRecord(message.content)?.reaction);
}

export function readReaction(message: Message): ReactionContent | null {
  const reaction = asRecord(asRecord(message.content)?.reaction);
  if (!reaction) return null;
  return {
    targetWamid: str(reaction.message_id),
    emoji: str(reaction.emoji) ?? "",
  };
}

/** Plain text — inbound normalises to `{body}`, outbound to `{text:{body}}`. */
export function readText(content: Content): string | null {
  const record = asRecord(content);
  if (!record) return null;
  const text = record.text;
  if (typeof text === "string") return text;
  const nested = asRecord(text);
  if (nested) return str(nested.body);
  return str(record.body);
}

export function readMedia(message: Message): MediaContent | null {
  const media = asRecord(asRecord(message.content)?.media);
  if (!media) return null;
  return {
    // Outbound carries `kind`; inbound infers it from the ledger's message_type.
    kind: str(media.kind) ?? message.message_type,
    caption: str(media.caption),
    filename: str(media.filename),
    mimeType: str(media.mime_type),
    link: str(media.link),
  };
}

export function readTemplate(message: Message): TemplateContent | null {
  const template = asRecord(asRecord(message.content)?.template);
  if (!template) return null;
  const language = template.language;
  return {
    name: str(template.name) ?? "template",
    language: str(language) ?? str(asRecord(language)?.code),
  };
}

export function readLocation(message: Message): { latitude?: number; longitude?: number; name: string | null } | null {
  const location = asRecord(asRecord(message.content)?.location);
  if (!location) return null;
  return {
    latitude: typeof location.latitude === "number" ? location.latitude : undefined,
    longitude: typeof location.longitude === "number" ? location.longitude : undefined,
    name: str(location.name),
  };
}

/** A tapped quick-reply/list option. */
export function readInteractive(message: Message): string | null {
  const interactive = asRecord(asRecord(message.content)?.interactive);
  if (!interactive) return null;
  const reply =
    asRecord(interactive.button_reply) ?? asRecord(interactive.list_reply) ?? interactive;
  return str(reply.title) ?? str(reply.text) ?? str(interactive.type);
}

/**
 * Attach reactions to the messages they target and drop them from the main flow — a reaction is a
 * ledger message of its own, but it reads as an annotation on another message.
 */
export function collateReactions(messages: Message[]): {
  thread: Message[];
  reactions: Map<string, ReactionContent[]>;
} {
  const byWamid = new Map<string, string>();
  for (const message of messages) {
    if (message.wamid) byWamid.set(message.wamid, message.id);
  }

  const reactions = new Map<string, ReactionContent[]>();
  const thread: Message[] = [];

  for (const message of messages) {
    if (!isReaction(message)) {
      thread.push(message);
      continue;
    }
    const reaction = readReaction(message);
    // An empty emoji clears a prior reaction (Doc 04 §18.2 v1.4).
    if (!reaction?.targetWamid || !reaction.emoji) continue;
    const targetId = byWamid.get(reaction.targetWamid);
    if (!targetId) continue; // the target is outside the loaded window
    reactions.set(targetId, [...(reactions.get(targetId) ?? []), reaction]);
  }

  return { thread, reactions };
}
