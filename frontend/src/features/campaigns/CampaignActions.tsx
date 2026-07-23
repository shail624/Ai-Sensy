import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  apiErrorMessage,
  useCancelCampaign,
  useDeleteCampaign,
  useDispatchCampaign,
  usePauseCampaign,
  useResumeCampaign,
  useRetryCampaign,
  useHasPermission,
} from "@/features/campaigns/api";
import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { formatCount } from "@/features/campaigns/format";
import type { Campaign } from "@/features/campaigns/types";
import {
  isCancellable,
  isDispatchable,
  isEditable,
  isPausable,
  isResumable,
  isRetryable,
} from "@/features/campaigns/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

type Confirmation = "dispatch" | "cancel" | "delete" | null;

interface Props {
  campaign: Campaign;
  /** After a delete the detail page must leave; the list just refreshes in place. */
  onDeleted?: () => void;
  /** Opens the schedule dialog — offered on the detail page, where there is room for it. */
  onSchedule?: () => void;
}

/**
 * The campaign action set (FR-CAM-05..09), gated twice over.
 *
 * **By permission**, using the same codes the API enforces (Doc 04 §17): `campaigns:write` to edit,
 * duplicate and delete; `campaigns:send` to dispatch, schedule and retry; `campaigns:manage` to
 * pause, resume and cancel. **By status**, using the lifecycle predicates in `types.ts`. A control
 * the server would refuse is never rendered, so the UI does not offer what it cannot deliver — but
 * the server stays the authority, and its 409 is surfaced verbatim when a race loses.
 *
 * One implementation, used identically by the list rows and the detail page.
 */
export function CampaignActions({ campaign, onDeleted, onSchedule }: Props): JSX.Element {
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState<Confirmation>(null);

  const canWrite = useHasPermission("campaigns:write");
  const canSend = useHasPermission("campaigns:send");
  const canManage = useHasPermission("campaigns:manage");

  const dispatch = useDispatchCampaign();
  const pause = usePauseCampaign();
  const resume = useResumeCampaign();
  const cancel = useCancelCampaign();
  const retry = useRetryCampaign();
  const remove = useDeleteCampaign();

  const pending =
    dispatch.isPending ||
    pause.isPending ||
    resume.isPending ||
    cancel.isPending ||
    retry.isPending ||
    remove.isPending;

  // Inline errors are for the actions taken directly; the confirmed ones report inside the dialog.
  const inlineError = pause.error ?? resume.error ?? retry.error;

  const editable = isEditable(campaign);

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {canWrite && editable ? (
          <button
            type="button"
            className={ACTION_CLASS}
            onClick={() => navigate(`/campaigns/${campaign.id}/edit`)}
          >
            Edit
          </button>
        ) : null}

        {canWrite ? (
          <button
            type="button"
            className={ACTION_CLASS}
            // Duplicate is composed from the endpoints that exist: the wizard opens prefilled from
            // this campaign and creates a new draft. Nothing is copied server-side.
            onClick={() => navigate("/campaigns/new", { state: { duplicateOf: campaign } })}
          >
            Duplicate
          </button>
        ) : null}

        {canSend && isDispatchable(campaign) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => setConfirming("dispatch")}
          >
            Send now
          </button>
        ) : null}

        {canSend && onSchedule && isDispatchable(campaign) ? (
          <button type="button" className={ACTION_CLASS} disabled={pending} onClick={onSchedule}>
            Schedule
          </button>
        ) : null}

        {canManage && isPausable(campaign) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => pause.mutate(campaign.id)}
          >
            Pause
          </button>
        ) : null}

        {canManage && isResumable(campaign) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => resume.mutate(campaign.id)}
          >
            Resume
          </button>
        ) : null}

        {canSend && isRetryable(campaign) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => retry.mutate(campaign.id)}
          >
            Retry {formatCount(campaign.failed_count)} failed
          </button>
        ) : null}

        {canManage && isCancellable(campaign) && !editable ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() => setConfirming("cancel")}
          >
            Cancel
          </button>
        ) : null}

        {canWrite && editable ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={pending}
            onClick={() => setConfirming("delete")}
          >
            Delete
          </button>
        ) : null}
      </div>

      {inlineError ? <p className="text-xs text-danger">{apiErrorMessage(inlineError)}</p> : null}

      {confirming === "dispatch" ? (
        <ConfirmDialog
          title="Send this campaign?"
          body={`This sends the template to ${formatCount(
            campaign.total_recipients,
          )} recipients on WhatsApp. Messages already handed to Meta cannot be unsent — you can pause or cancel what has not gone out yet.`}
          confirmLabel="Send now"
          pending={dispatch.isPending}
          error={dispatch.error}
          onClose={() => setConfirming(null)}
          onConfirm={() =>
            dispatch.mutate(campaign.id, { onSuccess: () => setConfirming(null) })
          }
        />
      ) : null}

      {confirming === "cancel" ? (
        <ConfirmDialog
          title="Cancel this campaign?"
          body="Recipients that have not been sent yet are dropped and the campaign stops for good. Messages already delivered are unaffected."
          confirmLabel="Cancel campaign"
          destructive
          pending={cancel.isPending}
          error={cancel.error}
          onClose={() => setConfirming(null)}
          onConfirm={() => cancel.mutate(campaign.id, { onSuccess: () => setConfirming(null) })}
        />
      ) : null}

      {confirming === "delete" ? (
        <ConfirmDialog
          title="Delete this draft?"
          body={`"${campaign.name}" and its audience roster are removed. Only a draft can be deleted.`}
          confirmLabel="Delete draft"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setConfirming(null)}
          onConfirm={() =>
            remove.mutate(campaign.id, {
              onSuccess: () => {
                setConfirming(null);
                onDeleted?.();
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
