import { formatCount, formatRate } from "@/features/campaigns/format";
import { completionRatio } from "@/features/campaigns/selectors";
import type { AudienceType, Campaign } from "@/features/campaigns/types";
import {
  AUDIENCE_TYPE_LABELS,
  CAMPAIGN_STATUS_LABELS,
  RECIPIENT_STATUS_LABELS,
} from "@/features/campaigns/types";

/** Status → chip tone. Unknown statuses fall back to the neutral border (see `types.ts`). */
const STATUS_TONE: Record<string, string> = {
  draft: "border-border text-text-secondary",
  scheduled: "border-info text-info",
  queued: "border-info text-info",
  running: "border-accent text-accent",
  paused: "border-warning text-warning",
  completed: "border-success text-success",
  cancelled: "border-border text-text-disabled",
  failed: "border-danger text-danger",
};

const RECIPIENT_TONE: Record<string, string> = {
  pending: "border-border text-text-secondary",
  queued: "border-info text-info",
  sent: "border-info text-info",
  delivered: "border-success text-success",
  read: "border-success text-success",
  failed: "border-danger text-danger",
  skipped: "border-border text-text-disabled",
  cancelled: "border-border text-text-disabled",
};

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function CampaignStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(STATUS_TONE[value] ?? "border-border text-text-primary")}>
      {CAMPAIGN_STATUS_LABELS[value] ?? value}
    </span>
  );
}

export function RecipientStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(RECIPIENT_TONE[value] ?? "border-border text-text-primary")}>
      {RECIPIENT_STATUS_LABELS[value] ?? value}
    </span>
  );
}

export function AudienceChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip("border-border text-text-secondary")}>
      {AUDIENCE_TYPE_LABELS[value as AudienceType] ?? value}
    </span>
  );
}

interface ProgressProps {
  campaign: Campaign;
  /** Compact rendering for table rows; the detail page uses the full bar with its caption. */
  compact?: boolean;
}

/**
 * How far the roster has been worked through (FR-CAM-10). An empty roster has no ratio to show —
 * a 0% bar would claim the campaign has 100% left to do, which is not the same as "nothing to do".
 */
export function CampaignProgressBar({ campaign, compact = false }: ProgressProps): JSX.Element {
  const ratio = completionRatio(campaign);
  const percent = ratio === null ? 0 : Math.round(ratio * 100);
  const handled = campaign.sent_count + campaign.failed_count;

  return (
    <div className={compact ? "w-32" : "w-full"}>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={`${campaign.name} progress`}
        className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
      >
        <div
          className={`h-full rounded-full ${
            campaign.failed_count > 0 && handled === campaign.failed_count
              ? "bg-danger"
              : "bg-accent"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className={`mt-1 text-xs text-text-secondary ${compact ? "truncate" : ""}`}>
        {ratio === null
          ? "No recipients"
          : `${formatCount(handled)} of ${formatCount(campaign.total_recipients)} (${formatRate(ratio)})`}
      </p>
    </div>
  );
}

interface StatProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "danger" | "success";
}

/** One delivery-statistic tile. Presentation only — the arithmetic lives in `selectors.ts`. */
export function StatTile({ label, value, hint, tone = "default" }: StatProps): JSX.Element {
  const valueTone =
    tone === "danger" ? "text-danger" : tone === "success" ? "text-success" : "text-text-primary";
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <p className="text-xs font-medium text-text-secondary">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${valueTone}`}>{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-text-disabled">{hint}</p> : null}
    </div>
  );
}
