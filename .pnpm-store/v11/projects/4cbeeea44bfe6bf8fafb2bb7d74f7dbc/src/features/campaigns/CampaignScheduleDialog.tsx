import { useState } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useScheduleCampaign } from "@/features/campaigns/api";
import { CampaignScheduleFields } from "@/features/campaigns/CampaignScheduleFields";
import type { ScheduleDraft } from "@/features/campaigns/scheduleForm";
import { blankSchedule, toScheduleRequest, validateSchedule } from "@/features/campaigns/scheduleForm";
import type { Campaign } from "@/features/campaigns/types";

interface Props {
  campaign: Campaign;
  onClose: () => void;
}

/**
 * Attach a schedule to an existing campaign (FR-CAM-03/04).
 *
 * Nothing is sent on this path: the schedule is written and the campaign parks in `scheduled`, for
 * the scheduler tick to pick up when it comes due. Reuses the same fields the create wizard uses.
 */
export function CampaignScheduleDialog({ campaign, onClose }: Props): JSX.Element {
  const [draft, setDraft] = useState<ScheduleDraft>(blankSchedule);
  const [problem, setProblem] = useState<string | null>(null);
  const schedule = useScheduleCampaign();

  function submit(): void {
    const invalid = validateSchedule(draft);
    setProblem(invalid);
    if (invalid) return;
    schedule.mutate(
      { campaignId: campaign.id, body: toScheduleRequest(draft) },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title={`Schedule "${campaign.name}"`} onClose={onClose}>
      <CampaignScheduleFields draft={draft} onChange={setDraft} idPrefix="dialog-schedule" />

      {problem ? <p className="mt-3 text-sm text-danger">{problem}</p> : null}
      {schedule.error ? (
        <p className="mt-3 text-sm text-danger">{apiErrorMessage(schedule.error)}</p>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          disabled={schedule.isPending}
          className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={schedule.isPending}
          className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
        >
          {schedule.isPending ? "Scheduling…" : "Schedule"}
        </button>
      </div>
    </Modal>
  );
}
