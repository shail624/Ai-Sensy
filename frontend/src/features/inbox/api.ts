import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { createIdempotencyKey } from "@/lib/idempotency";
import type {
  Conversation,
  ConversationsPage,
  ConversationState,
  ConversationStatus,
  InboxFilters,
  MessagesPage,
  Note,
  QuickReply,
  TagSummary,
  UserSummary,
} from "@/features/inbox/types";

// Shared error helper, re-exported for this feature's components.
export { apiErrorMessage } from "@/lib/api/errors";

export const inboxKeys = {
  all: ["inbox"] as const,
  list: (filters: InboxFilters, cursor: string | null) =>
    ["inbox", "list", filters, cursor] as const,
  detail: (id: string) => ["inbox", "conversation", id] as const,
  messages: (id: string) => ["inbox", "conversation", id, "messages"] as const,
  notes: (id: string) => ["inbox", "conversation", id, "notes"] as const,
  quickReplies: ["quick-replies"] as const,
  assignees: ["users", "assignable"] as const,
};

/**
 * How often the inbox re-reads itself. The platform ships no realtime transport (the conversations
 * endpoint documents that explicitly), so freshness is polling: cheap, cursor-stable, and honest
 * about its latency. Swapping this for a socket later touches only this constant and the hooks.
 */
export const POLL_INTERVAL_MS = 10_000;

/** The inbox list filters, as the contract now declares them. */
export function toListQuery(filters: InboxFilters, cursor: string | null, limit: number) {
  return {
    contact: filters.contact || null,
    status: filters.status || null,
    assignee: filters.assignee || null,
    number: filters.number || null,
    tag: filters.tag ? [filters.tag] : null,
    q: filters.q || null,
    cursor: cursor || null,
    limit,
  };
}

export function useConversations(
  filters: InboxFilters,
  cursor: string | null,
  limit = 25,
  enabled = true,
) {
  return useQuery({
    queryKey: inboxKeys.list(filters, cursor),
    queryFn: async (): Promise<ConversationsPage> =>
      unwrap(
        await api.GET("/api/v1/conversations", {
          params: { query: toListQuery(filters, cursor, limit) },
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: POLL_INTERVAL_MS,
    enabled,
  });
}

/**
 * `refetchInterval` defaults to the live 10s poll every existing caller (Live Chat's thread view,
 * Customer 360's conversation section) relies on; a read-only consumer with no live-triage need
 * (Chat History) can pass `false` to read once per selection instead, without a second hook.
 */
export function useConversation(
  conversationId: string | null,
  refetchInterval: number | false = POLL_INTERVAL_MS,
) {
  return useQuery({
    queryKey: inboxKeys.detail(conversationId ?? ""),
    queryFn: async (): Promise<Conversation> =>
      unwrap(
        await api.GET("/api/v1/conversations/{conversation_id}", {
          params: { path: { conversation_id: conversationId! } },
        }),
      ),
    enabled: Boolean(conversationId),
    refetchInterval,
  });
}

/**
 * Message history, newest-first, one cursor page at a time. The first page polls for new messages
 * by default; older pages are fetched on demand by the thread's "Load older messages" control and
 * stay put. `refetchInterval` follows the same override convention as {@link useConversation}.
 */
export function useMessages(
  conversationId: string | null,
  limit = 50,
  refetchInterval: number | false = POLL_INTERVAL_MS,
) {
  return useInfiniteQuery({
    queryKey: inboxKeys.messages(conversationId ?? ""),
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }): Promise<MessagesPage> =>
      unwrap(
        await api.GET("/api/v1/conversations/{conversation_id}/messages", {
          params: {
            path: { conversation_id: conversationId! },
            query: { cursor: pageParam, limit },
          },
        }),
      ),
    getNextPageParam: (last) => (last.page.has_more ? (last.page.next_cursor ?? null) : null),
    enabled: Boolean(conversationId),
    refetchInterval,
  });
}

export function useNotes(conversationId: string | null) {
  return useQuery({
    queryKey: inboxKeys.notes(conversationId ?? ""),
    queryFn: async (): Promise<Note[]> =>
      unwrap(
        await api.GET("/api/v1/conversations/{conversation_id}/notes", {
          params: { path: { conversation_id: conversationId! } },
        }),
      ).data,
    enabled: Boolean(conversationId),
  });
}

export function useQuickReplies() {
  return useQuery({
    queryKey: inboxKeys.quickReplies,
    queryFn: async (): Promise<QuickReply[]> => unwrap(await api.GET("/api/v1/quick-replies")).data,
    staleTime: 5 * 60_000,
  });
}

/** Candidate assignees — the org's users (Doc 04 §12). */
export function useAssignableUsers() {
  return useQuery({
    queryKey: inboxKeys.assignees,
    queryFn: async (): Promise<UserSummary[]> => {
      const page = unwrap(await api.GET("/api/v1/users"));
      return page.data.map((user) => ({
        id: user.id,
        full_name: user.full_name,
        email: user.email,
        is_superuser: user.is_superuser,
      }));
    },
    staleTime: 5 * 60_000,
  });
}

/** Conversation mutations invalidate the thread and the list — both reflect the same state. */
function useConversationMutation<TVariables, TData>(
  conversationId: string,
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: inboxKeys.all });
      void queryClient.invalidateQueries({ queryKey: inboxKeys.detail(conversationId) });
    },
  });
}

export function useAssignConversation(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async (assigneeId: string): Promise<ConversationState> =>
      unwrap(
        await api.POST("/api/v1/conversations/{conversation_id}/assign", {
          params: { path: { conversation_id: conversationId } },
          body: { assignee_id: assigneeId },
        }),
      ),
  );
}

export function useSetConversationStatus(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async (status: ConversationStatus): Promise<ConversationState> =>
      unwrap(
        await api.POST("/api/v1/conversations/{conversation_id}/status", {
          params: { path: { conversation_id: conversationId } },
          body: { status },
        }),
      ),
  );
}

/** Composes the existing per-conversation status endpoint for a user-selected bulk operation. */
export function useBulkSetConversationStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status }: { ids: string[]; status: ConversationStatus }) => {
      await Promise.all(ids.map(async (conversationId) =>
        unwrap(await api.POST("/api/v1/conversations/{conversation_id}/status", {
          params: { path: { conversation_id: conversationId } },
          body: { status },
        })),
      ));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
  });
}

/** Composes the existing assignment endpoint; no batch contract or server behavior is introduced. */
export function useBulkAssignConversations() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, assigneeId }: { ids: string[]; assigneeId: string }) => {
      await Promise.all(ids.map(async (conversationId) =>
        unwrap(await api.POST("/api/v1/conversations/{conversation_id}/assign", {
          params: { path: { conversation_id: conversationId } },
          body: { assignee_id: assigneeId },
        })),
      ));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
  });
}

/** Composes the existing tag endpoint for selected threads; it does not invent a batch contract. */
export function useBulkAddConversationTags() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, tagId }: { ids: string[]; tagId: string }) => {
      await Promise.all(ids.map(async (conversationId) =>
        unwrap(await api.POST("/api/v1/conversations/{conversation_id}/tags", {
          params: { path: { conversation_id: conversationId } },
          body: { tag_ids: [tagId] },
        })),
      ));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
  });
}

export function useMarkRead(conversationId: string) {
  return useConversationMutation(conversationId, async () =>
    unwrap(
      await api.POST("/api/v1/conversations/{conversation_id}/read", {
        params: { path: { conversation_id: conversationId } },
      }),
    ),
  );
}

export function useAddNote(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async (body: string): Promise<Note> =>
      unwrap(
        await api.POST("/api/v1/conversations/{conversation_id}/notes", {
          params: { path: { conversation_id: conversationId } },
          body: { body },
        }),
      ),
  );
}

export function useDeleteNote(conversationId: string) {
  return useConversationMutation(conversationId, async (noteId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/conversations/{conversation_id}/notes/{note_id}", {
      params: { path: { conversation_id: conversationId, note_id: noteId } },
    });
    if (error !== undefined) throw error;
  });
}

export function useAddConversationTags(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async (tagIds: string[]): Promise<TagSummary[]> =>
      unwrap(
        await api.POST("/api/v1/conversations/{conversation_id}/tags", {
          params: { path: { conversation_id: conversationId } },
          body: { tag_ids: tagIds },
        }),
      ).data,
  );
}

export function useRemoveConversationTag(conversationId: string) {
  return useConversationMutation(conversationId, async (tagId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/conversations/{conversation_id}/tags/{tag_id}", {
      params: { path: { conversation_id: conversationId, tag_id: tagId } },
    });
    if (error !== undefined) throw error;
  });
}

/**
 * A reply to an open thread (QR-08). Conversation-scoped, not number-scoped: the provider is the
 * conversation's own durable ownership, decided entirely server-side — this request carries no
 * `phone_number_id`/provider field for a caller to set, forge, or need to get right.
 */
export function useSendMessage(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async ({ body }: { body: string }) =>
      unwrap(
        await api.POST("/api/v1/messages/send", {
          // Not a declared OpenAPI header parameter (the endpoint reads it off the raw request,
          // Doc 04 §8) — set via the fetch-level `headers` option rather than `params.header`.
          headers: { "Idempotency-Key": createIdempotencyKey() },
          body: {
            conversation_id: conversationId,
            type: "text",
            text: { body, preview_url: false },
          },
        }),
      ),
  );
}

export function useSendReaction(conversationId: string) {
  return useConversationMutation(
    conversationId,
    async ({ messageId, emoji }: { messageId: string; emoji: string }) =>
      unwrap(
        await api.POST("/api/v1/messages/{message_id}/reaction", {
          params: { path: { message_id: messageId } },
          body: { emoji },
        }),
      ),
  );
}
