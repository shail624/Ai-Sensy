import { Section, Spinner } from "@/components/ui";
import { CampaignProgressBar, StatTile } from "@/features/campaigns/CampaignBadges";
import { formatCount, formatRate } from "@/features/campaigns/format";
import { deliveryStats } from "@/features/campaigns/selectors";
import type { Campaign, CampaignProgress } from "@/features/campaigns/types";

interface Props {
  campaign: Campaign;
  progress: CampaignProgress | undefined;
  /** True while the campaign can still move, so the caption can say the numbers are live. */
  live: boolean;
  isLoadingProgress: boolean;
}

/**
 * Delivery statistics and live progress (FR-CAM-10).
 *
 * Two sources, deliberately: the tiles read the campaign's own counters, while the queue/batch
 * figures come from `/progress`, which derives them from the roster — the authority the counters
 * mirror. Showing both is what makes a stalled campaign visible.
 */
export function CampaignStats({ campaign, progress, live, isLoadingProgress }: Props): JSX.Element {
  const stats = deliveryStats(campaign);

  return (
    <div className="space-y-4">
      <Section title={live ? "Progress (live)" : "Progress"}>
        <CampaignProgressBar campaign={campaign} />
        {isLoadingProgress && !progress ? (
          <div className="mt-3">
            <Spinner label="Reading progress…" />
          </div>
        ) : progress ? (
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <Figure label="Pending" value={formatCount(progress.pending)} />
            <Figure label="Queued" value={formatCount(progress.queued)} />
            <Figure label="Sent" value={formatCount(progress.sent)} />
            <Figure label="Delivered" value={formatCount(progress.delivered)} />
            <Figure
              label="Batches"
              value={`${formatCount(progress.batches_done)} / ${formatCount(progress.batches_total)}`}
            />
          </dl>
        ) : null}
      </Section>

      <Section title="Delivery statistics">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <StatTile label="Recipients" value={formatCount(stats.total)} />
          <StatTile label="Sent" value={formatCount(stats.sent)} hint="Handed to WhatsApp" />
          <StatTile
            label="Delivered"
            value={formatCount(stats.delivered)}
            hint={`${formatRate(stats.deliveryRate)} of sent`}
            tone="success"
          />
          <StatTile
            label="Read"
            value={formatCount(stats.read)}
            hint={`${formatRate(stats.readRate)} of delivered`}
          />
          <StatTile
            label="Failed"
            value={formatCount(stats.failed)}
            hint={`${formatRate(stats.failureRate)} of recipients`}
            tone={stats.failed > 0 ? "danger" : "default"}
          />
        </div>
        <p className="mt-3 text-xs text-text-disabled">
          Replies: {formatCount(stats.replied)} ({formatRate(stats.replyRate)} of delivered). Rates
          follow the funnel — delivery is measured against what was sent, reads against what was
          delivered — so a campaign still fanning out is not reported as failing.
        </p>
      </Section>
    </div>
  );
}

function Figure({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div>
      <dt className="text-xs font-medium text-text-secondary">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold text-text-primary">{value}</dd>
    </div>
  );
}
