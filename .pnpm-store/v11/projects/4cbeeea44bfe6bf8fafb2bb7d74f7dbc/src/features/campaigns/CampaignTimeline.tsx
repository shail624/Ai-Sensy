import { Section } from "@/components/ui";
import { formatCount, formatDateTime } from "@/features/campaigns/format";
import type { Campaign, CampaignProgress } from "@/features/campaigns/types";
import { isTerminal } from "@/features/campaigns/types";

type StageState = "done" | "current" | "pending" | "skipped";

interface Stage {
  key: string;
  label: string;
  detail: string;
  state: StageState;
}

const DOT: Record<StageState, string> = {
  done: "bg-success",
  current: "bg-accent",
  pending: "bg-border",
  skipped: "bg-border",
};

/**
 * The campaign's lifecycle, from the state the API exposes (FR-CAM-05..09).
 *
 * Built from the campaign row and `/progress` rather than an event log: per-action history lives in
 * the audit log, whose endpoint declares no entity filter in the contract, so it cannot be queried
 * for one campaign from here. What is shown is therefore the stages reached and the timestamps the
 * campaign itself carries — accurate, and honest about its resolution.
 */
export function CampaignTimeline({
  campaign,
  progress,
}: {
  campaign: Campaign;
  progress: CampaignProgress | undefined;
}): JSX.Element {
  const stages = buildStages(campaign, progress);

  return (
    <Section title="Timeline">
      <ol className="space-y-3">
        {stages.map((stage) => (
          <li key={stage.key} className="flex gap-3">
            <span
              aria-hidden
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${DOT[stage.state]}`}
            />
            <div className="min-w-0">
              <p
                className={`text-sm ${
                  stage.state === "pending" || stage.state === "skipped"
                    ? "text-text-disabled"
                    : "text-text-primary"
                }`}
              >
                {stage.label}
              </p>
              <p className="text-xs text-text-secondary">{stage.detail}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-text-disabled">
        Stage history is derived from the current state of this campaign; per-action history is
        recorded in the audit log.
      </p>
    </Section>
  );
}

function buildStages(campaign: Campaign, progress: CampaignProgress | undefined): Stage[] {
  const status = campaign.status;
  const started = status !== "draft";
  const finished = isTerminal(campaign);
  const handled = campaign.sent_count + campaign.failed_count;

  const stages: Stage[] = [
    {
      key: "created",
      label: "Draft created",
      detail: formatDateTime(campaign.created_at),
      state: "done",
    },
    {
      key: "audience",
      label: "Audience resolved",
      detail:
        campaign.total_recipients > 0
          ? `${formatCount(campaign.total_recipients)} recipients on the roster`
          : "No recipients on the roster",
      state: campaign.total_recipients > 0 ? "done" : "pending",
    },
  ];

  if (status === "scheduled") {
    stages.push({
      key: "scheduled",
      label: "Scheduled",
      detail: "Waiting for its slot — the scheduler fires it when it comes due.",
      state: "current",
    });
  }

  stages.push({
    key: "dispatch",
    label: "Handed to the send queue",
    detail: progress
      ? `${formatCount(progress.batches_done)} of ${formatCount(progress.batches_total)} batches complete`
      : started
        ? "Dispatched"
        : "Not dispatched yet",
    state: started ? (status === "queued" ? "current" : "done") : "pending",
  });

  stages.push({
    key: "sending",
    label: "Sending",
    detail:
      handled > 0
        ? `${formatCount(handled)} of ${formatCount(campaign.total_recipients)} handled`
        : "Nothing sent yet",
    state: status === "running" ? "current" : handled > 0 ? "done" : "pending",
  });

  if (status === "paused") {
    stages.push({
      key: "paused",
      label: "Paused",
      detail: "Sending stopped; nothing further goes out until it is resumed.",
      state: "current",
    });
  }

  stages.push({
    key: "finished",
    label:
      status === "cancelled"
        ? "Cancelled"
        : status === "failed"
          ? "Failed"
          : "Completed",
    detail: finished
      ? `${formatDateTime(campaign.updated_at)} · ${formatCount(campaign.sent_count)} sent, ${formatCount(campaign.failed_count)} failed`
      : "Not finished yet",
    state: finished ? (status === "completed" ? "done" : "skipped") : "pending",
  });

  return stages;
}
