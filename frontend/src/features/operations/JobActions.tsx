import { useState } from "react";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { apiErrorMessage, useCancelJob, useHasPermission } from "@/features/operations/api";
import type { Job } from "@/features/operations/types";
import { isCancellable } from "@/features/operations/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  job: Job;
  onCancelled?: () => void;
}

/**
 * The job action set — cancel, and only cancel.
 *
 * That is not an omission: `POST /jobs/{id}/cancel` is the **only** mutating job endpoint the
 * backend exposes. There is no retry route, and the dead-letter replay that would serve as one is
 * implemented in the service layer but not mounted on any router — so no retry control is offered
 * here, because none could work.
 *
 * Gated by `system:manage` (reads need only `system:read`), and by state: a job that has already
 * finished cannot be cancelled and the server answers 409.
 */
export function JobActions({ job, onCancelled }: Props): JSX.Element {
  const [confirming, setConfirming] = useState(false);
  const canManage = useHasPermission("system:manage");
  const cancel = useCancelJob();

  if (!canManage || !isCancellable(job)) {
    return (
      <span className="text-xs text-text-disabled">
        {!canManage ? "" : "Finished"}
      </span>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        className={`${ACTION_CLASS} text-danger`}
        disabled={cancel.isPending}
        onClick={() => setConfirming(true)}
      >
        Cancel
      </button>

      {cancel.error && !confirming ? (
        <p className="text-xs text-danger">{apiErrorMessage(cancel.error)}</p>
      ) : null}

      {confirming ? (
        <ConfirmDialog
          title="Cancel this job?"
          body={
            job.status === "started"
              ? "The job is running now. Cancelling revokes it without terminating the worker, so the attempt in flight finishes on its own — what stops is any further attempt. Work it has already committed is not rolled back."
              : "The job will not be handed to a worker. Nothing it was going to do will happen."
          }
          confirmLabel="Cancel job"
          destructive
          pending={cancel.isPending}
          error={cancel.error}
          onClose={() => setConfirming(false)}
          onConfirm={() =>
            cancel.mutate(job.id, {
              onSuccess: () => {
                setConfirming(false);
                onCancelled?.();
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
