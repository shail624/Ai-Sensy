import { useState } from "react";

import { TagChip } from "@/components/ui";
import {
  useAddConversationTags,
  useAssignConversation,
  useAssignableUsers,
  useRemoveConversationTag,
  useSetConversationStatus,
} from "@/features/inbox/api";
import type { Conversation, ConversationStatus, TagSummary } from "@/features/inbox/types";
import { CONVERSATION_STATUSES, STATUS_LABELS } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary disabled:opacity-50";

/** Assignment control — reassigning to another agent requires `inbox:assign` (Doc 12). */
export function AssignmentControl({ conversation }: { conversation: Conversation }): JSX.Element {
  const canAssign = useHasPermission("inbox:assign");
  const users = useAssignableUsers();
  const assign = useAssignConversation(conversation.id);

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="conv-assignee" className="text-xs font-medium text-text-secondary">
        Assigned to
      </label>
      <select
        id="conv-assignee"
        value={conversation.assigned_to ?? ""}
        disabled={!canAssign || assign.isPending}
        onChange={(event) => {
          if (event.target.value) assign.mutate(event.target.value);
        }}
        className={FIELD_CLASS}
      >
        <option value="">Unassigned</option>
        {(users.data ?? []).map((user) => (
          <option key={user.id} value={user.id}>
            {user.full_name}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Status control — open · pending · resolved · snoozed (Doc 04 §18.1). */
export function StatusControl({ conversation }: { conversation: Conversation }): JSX.Element {
  const canWrite = useHasPermission("inbox:write");
  const setStatus = useSetConversationStatus(conversation.id);

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="conv-status" className="text-xs font-medium text-text-secondary">
        Status
      </label>
      <select
        id="conv-status"
        value={conversation.status}
        disabled={!canWrite || setStatus.isPending}
        onChange={(event) => setStatus.mutate(event.target.value as ConversationStatus)}
        className={FIELD_CLASS}
      >
        {CONVERSATION_STATUSES.map((status) => (
          <option key={status} value={status}>
            {STATUS_LABELS[status]}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Conversation tags (FR-INB-07) — add from the org catalogue, remove inline. */
export function ConversationTags({
  conversation,
  tags,
}: {
  conversation: Conversation;
  tags: TagSummary[];
}): JSX.Element {
  const canWrite = useHasPermission("inbox:write");
  const [adding, setAdding] = useState("");
  const addTags = useAddConversationTags(conversation.id);
  const removeTag = useRemoveConversationTag(conversation.id);

  const attached = new Set(conversation.tags.map((tag) => tag.id));
  const available = tags.filter((tag) => !attached.has(tag.id));

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-text-secondary">Tags</span>
      <div className="flex flex-wrap items-center gap-1">
        {conversation.tags.map((tag) => (
          <TagChip
            key={tag.id}
            name={tag.name}
            color={tag.color}
            onRemove={canWrite ? () => removeTag.mutate(tag.id) : undefined}
            removing={removeTag.isPending}
          />
        ))}
        {conversation.tags.length === 0 ? (
          <span className="text-xs text-text-disabled">None</span>
        ) : null}
      </div>

      {canWrite && available.length > 0 ? (
        <>
          <label htmlFor="conv-add-tag" className="sr-only">
            Add tag
          </label>
          <select
            id="conv-add-tag"
            value={adding}
            disabled={addTags.isPending}
            onChange={(event) => {
              const tagId = event.target.value;
              setAdding("");
              if (tagId) addTags.mutate([tagId]);
            }}
            className={FIELD_CLASS}
          >
            <option value="">Add a tag…</option>
            {available.map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </>
      ) : null}
    </div>
  );
}
