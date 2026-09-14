import { CircleCheck, Hand } from "lucide-react";

import { Badge, Button } from "@/components/ui";
import {
  apiErrorMessage,
  useInterveneConversation,
  useResolveIntervention,
} from "@/features/inbox/api";
import type { Conversation } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";

interface Props {
  conversation: Conversation;
  currentUserId?: string;
}

/** The one-click AiSensy-style request → intervention → resolution operator path. */
export function InterventionActions({ conversation, currentUserId }: Props): JSX.Element | null {
  const canWrite = useHasPermission("inbox:write");
  const intervene = useInterveneConversation(conversation.id);
  const resolve = useResolveIntervention(conversation.id);

  if (!canWrite || !currentUserId) return null;

  const assignedToAnother = Boolean(
    conversation.assigned_to && conversation.assigned_to !== currentUserId,
  );
  const error = intervene.error ?? resolve.error;

  if (conversation.status === "pending" && assignedToAnother) {
    return <Badge tone="warning">Owned by another agent</Badge>;
  }

  const action =
    conversation.status === "pending" ? (
      <Button
        type="button"
        size="sm"
        loading={intervene.isPending}
        leftIcon={<Hand aria-hidden className="h-4 w-4" />}
        onClick={() => intervene.mutate(undefined)}
      >
        Intervene
      </Button>
    ) : conversation.status === "open" && conversation.assigned_to === currentUserId ? (
      <Button
        type="button"
        size="sm"
        variant="secondary"
        loading={resolve.isPending}
        leftIcon={<CircleCheck aria-hidden className="h-4 w-4" />}
        onClick={() => resolve.mutate(undefined)}
      >
        Resolve
      </Button>
    ) : null;

  if (!action) return null;

  return (
    <div className="flex flex-col items-end gap-1">
      {action}
      {error ? (
        <p role="alert" className="max-w-48 text-right text-[11px] text-danger">
          {apiErrorMessage(error)}
        </p>
      ) : null}
    </div>
  );
}
