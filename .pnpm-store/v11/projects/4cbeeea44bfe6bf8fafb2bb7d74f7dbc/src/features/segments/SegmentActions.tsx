import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import {
  apiErrorMessage,
  useDeleteSegment,
  useHasPermission,
  useRefreshSegment,
} from "@/features/segments/api";
import type { Segment } from "@/features/segments/types";
import { isStale } from "@/features/segments/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  segment: Segment;
  /** After a delete the detail page must leave; the list just refreshes in place. */
  onDeleted?: () => void;
  /** Edit and duplicate need room; the compact list rows leave them to the detail page. */
  compact?: boolean;
}

/**
 * The segment action set (Doc 04 §14.3), gated twice over.
 *
 * **By permission** — `segments:write` to edit, duplicate and delete; **refresh needs only
 * `segments:read`**, because recomputing a size is a read of the contact set, and the endpoint is
 * gated that way deliberately.
 *
 * The delete confirmation is blunt about a real gap: the server applies **no usage guard**, so a
 * segment a campaign targets can be deleted and that campaign's audience will stop resolving.
 */
export function SegmentActions({ segment, onDeleted, compact = false }: Props): JSX.Element {
  const navigate = useNavigate();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const canRead = useHasPermission("segments:read");
  const canWrite = useHasPermission("segments:write");

  const refresh = useRefreshSegment();
  const remove = useDeleteSegment();

  const pending = refresh.isPending || remove.isPending;

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {canRead ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => refresh.mutate(segment.id)}
          >
            {refresh.isPending ? "Counting…" : isStale(segment) ? "Evaluate" : "Refresh count"}
          </button>
        ) : null}

        {canWrite && !compact ? (
          <button
            type="button"
            className={ACTION_CLASS}
            onClick={() => navigate(`/segments/${segment.id}/edit`)}
          >
            Edit
          </button>
        ) : null}

        {canWrite ? (
          <button
            type="button"
            className={ACTION_CLASS}
            // Duplicate is composed from the endpoints that exist: the editor opens prefilled from
            // this segment and creates a new one. Nothing is copied server-side.
            onClick={() => navigate("/segments/new", { state: { duplicateOf: segment } })}
          >
            Duplicate
          </button>
        ) : null}

        {canWrite ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={pending}
            onClick={() => setConfirmingDelete(true)}
          >
            Delete
          </button>
        ) : null}
      </div>

      {refresh.error ? (
        <p className="text-xs text-danger">{apiErrorMessage(refresh.error)}</p>
      ) : null}
      {remove.error && !confirmingDelete ? (
        <p className="text-xs text-danger">{apiErrorMessage(remove.error)}</p>
      ) : null}

      {confirmingDelete ? (
        <ConfirmDialog
          title={`Delete "${segment.name}"?`}
          body="The platform does not check whether anything uses this segment. Any campaign targeting it will stop resolving an audience — check that first. Contacts themselves are unaffected."
          confirmLabel="Delete segment"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setConfirmingDelete(false)}
          onConfirm={() =>
            remove.mutate(segment.id, {
              onSuccess: () => {
                setConfirmingDelete(false);
                onDeleted?.();
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
