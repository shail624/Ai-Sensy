import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written.
export type Conversation = components["schemas"]["ConversationResponse"];
export type ConversationsPage = components["schemas"]["ConversationsPage"];
export type ConversationState = components["schemas"]["ConversationStateResponse"];
export type Message = components["schemas"]["MessageResponse"];
export type MessagesPage = components["schemas"]["ConversationMessagesPage"];
export type Note = components["schemas"]["NoteResponse"];
export type QuickReply = components["schemas"]["QuickReplyResponse"];
export type TagSummary = components["schemas"]["TagSummary"];
export type UserSummary = components["schemas"]["UserSummary"];
export type PhoneNumber = components["schemas"]["PhoneNumberResponse"];

/** Conversation status, taken from the request schema's enum so it cannot drift. */
export type ConversationStatus =
  components["schemas"]["ConversationStatusRequest"]["status"];

export const CONVERSATION_STATUSES: ConversationStatus[] = [
  "open",
  "pending",
  "resolved",
  "snoozed",
];

export const STATUS_LABELS: Record<ConversationStatus, string> = {
  open: "Open",
  pending: "Pending",
  resolved: "Resolved",
  snoozed: "Snoozed",
};

/**
 * The inbox list filters (Doc 04 §18.1).
 *
 * These are read by the backend straight off `request.query_params`, so FastAPI never declared them
 * and the generated contract types the query as `never`. They are sent through openapi-fetch's
 * `querySerializer` instead — the response stays fully generated. See `serializeInboxQuery`.
 */
export interface InboxFilters {
  status?: string;
  assignee?: string;
  tag?: string;
  q?: string;
}

/** Emoji offered by the reaction picker (the API accepts any single emoji). */
export const REACTION_EMOJI = ["👍", "❤️", "😂", "😮", "😢", "🙏"];
