import { useState } from "react";

import {
  apiErrorMessage,
  useHasPermission,
  useRefreshNumber,
} from "@/features/channels/api";
import { NumberEditDialog } from "@/features/channels/NumberEditDialog";
import type { PhoneNumber } from "@/features/channels/types";
import { WhatsAppChatLinkDialog } from "@/features/channels/WhatsAppChatLinkDialog";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  number: PhoneNumber;
  /** Edit needs room; the compact list rows leave it to the detail page. */
  compact?: boolean;
}

/**
 * The phone-number action set (Doc 04 §13.3).
 *
 * Two actions, because two are all the backend has: refresh re-pulls health and limits from Meta,
 * and edit changes the three operator-owned fields. There is no add or delete — numbers exist
 * because a WABA sync found them, and the platform does not create or remove them.
 *
 * Refresh is the one call here that reaches Meta, so it fails as `502 channel_error` when the
 * channel or the stored credential is at fault. That is a different problem from a bad request,
 * and the message says which.
 */
export function NumberActions({ number, compact = false }: Props): JSX.Element {
  const [editing, setEditing] = useState(false);
  const [sharing, setSharing] = useState(false);
  const canManage = useHasPermission("waba:manage");
  const refresh = useRefreshNumber();

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {canManage ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={refresh.isPending}
            onClick={() => refresh.mutate(number.id)}
          >
            {refresh.isPending ? "Refreshing…" : "Refresh"}
          </button>
        ) : null}

        {canManage && !compact ? (
          <button type="button" className={ACTION_CLASS} onClick={() => setEditing(true)}>
            Edit
          </button>
        ) : null}

        {!compact ? (
          <button type="button" className={ACTION_CLASS} onClick={() => setSharing(true)}>
            Chat link &amp; QR
          </button>
        ) : null}
      </div>

      {refresh.isSuccess ? <p className="text-xs text-success">Updated from Meta.</p> : null}
      {refresh.error ? (
        <p className="text-xs text-danger">{apiErrorMessage(refresh.error)}</p>
      ) : null}

      {editing ? <NumberEditDialog number={number} onClose={() => setEditing(false)} /> : null}
      {sharing ? <WhatsAppChatLinkDialog number={number} onClose={() => setSharing(false)} /> : null}
    </div>
  );
}
