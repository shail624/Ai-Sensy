import { useState } from "react";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import {
  apiErrorMessage,
  useDisconnectWaba,
  useHasPermission,
  useSyncWaba,
  useUpdateWaba,
} from "@/features/channels/api";
import { WabaFormDialog } from "@/features/channels/WabaFormDialog";
import type { Waba } from "@/features/channels/types";
import { isDisconnectable, isReactivatable } from "@/features/channels/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  waba: Waba;
  /** After a disconnect the detail page must leave; the list just refreshes in place. */
  onDisconnected?: () => void;
  /** Edit needs room; the compact list rows leave it to the detail page. */
  compact?: boolean;
}

/**
 * The WABA action set (Doc 04 §13.2), gated twice over.
 *
 * **By permission** — `waba:manage` for every write, `waba:read` to see the account at all. **By
 * state** — an account that still owns numbers cannot be disconnected (the server answers 409), and
 * an already-active account has no reactivation to offer.
 *
 * There is deliberately no "reconnect": disconnecting soft-deletes the row but keeps Meta's globally
 * unique WABA id, and the duplicate check ignores soft-deletion, so the same account can never be
 * connected again from here. The confirm dialog says exactly that rather than implying it is
 * reversible.
 */
export function WabaActions({ waba, onDisconnected, compact = false }: Props): JSX.Element {
  const [editing, setEditing] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  const canManage = useHasPermission("waba:manage");
  const sync = useSyncWaba();
  const update = useUpdateWaba();
  const disconnect = useDisconnectWaba();

  const pending = sync.isPending || update.isPending || disconnect.isPending;
  const inlineError = sync.error ?? update.error;

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {canManage ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => sync.mutate(waba.id)}
          >
            {sync.isPending ? "Starting…" : "Sync numbers"}
          </button>
        ) : null}

        {canManage && isReactivatable(waba) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() =>
              update.mutate({
                wabaId: waba.id,
                body: { status: "active", row_version: waba.row_version },
              })
            }
          >
            Reactivate
          </button>
        ) : null}

        {canManage && !compact ? (
          <button type="button" className={ACTION_CLASS} onClick={() => setEditing(true)}>
            Edit
          </button>
        ) : null}

        {canManage && !compact && isDisconnectable(waba) ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={pending}
            onClick={() => setDisconnecting(true)}
          >
            Disconnect
          </button>
        ) : null}
      </div>

      {canManage && !compact && !isDisconnectable(waba) ? (
        <p className="text-xs text-text-disabled">
          Has {waba.phone_number_count} number{waba.phone_number_count === 1 ? "" : "s"} — cannot be
          disconnected
        </p>
      ) : null}

      {sync.isSuccess ? (
        <p className="text-xs text-info">
          Sync started. Numbers appear here once it finishes.
        </p>
      ) : null}

      {inlineError ? <p className="text-xs text-danger">{apiErrorMessage(inlineError)}</p> : null}

      {editing ? <WabaFormDialog waba={waba} onClose={() => setEditing(false)} /> : null}

      {disconnecting ? (
        <ConfirmDialog
          title={`Disconnect ${waba.business_name}?`}
          body="This cannot be undone from the platform: Meta's WABA id stays reserved by the disconnected record, so this account cannot be connected again here. Suspend it instead if you only need to stop it temporarily."
          confirmLabel="Disconnect permanently"
          destructive
          pending={disconnect.isPending}
          error={disconnect.error}
          onClose={() => setDisconnecting(false)}
          onConfirm={() =>
            disconnect.mutate(waba.id, {
              onSuccess: () => {
                setDisconnecting(false);
                onDisconnected?.();
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
