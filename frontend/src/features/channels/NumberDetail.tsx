import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useNumber,
  useNumberHealth,
  useWaba,
} from "@/features/channels/api";
import {
  DefaultChip,
  HealthChip,
  MetaValueChip,
  NumberStatusChip,
  QualityChip,
} from "@/features/channels/ChannelBadges";
import { NumberActions } from "@/features/channels/NumberActions";
import type { PhoneNumber } from "@/features/channels/types";
import { QUALITY_EXPLANATIONS } from "@/features/channels/types";
// The campaigns feature owns campaign reads; importing its hook shares one cache rather than
// growing a second query for the same endpoint.
import { useCampaigns } from "@/features/campaigns/api";
import { formatAge, formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

/**
 * One phone number in full (Doc 05 B11.6) — what it is, what Meta thinks of it, how fast it may
 * send, and which campaigns are pointed at it.
 */
export function NumberDetail({ numberId }: { numberId: string }): JSX.Element {
  const number = useNumber(numberId);

  if (number.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading number…" />
      </PageContainer>
    );
  }

  if (number.isError || !number.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Numbers", to: "/channels/numbers" }, { label: "Number" }]} />
        <ErrorState message={apiErrorMessage(number.error)} onRetry={() => void number.refetch()} />
      </PageContainer>
    );
  }

  const data = number.data;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[{ label: "Numbers", to: "/channels/numbers" }, { label: data.display_number }]}
      />
      <PageHeader
        title={data.display_number}
        description={data.verified_name ?? "No display name set"}
        actions={<NumberActions number={data} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <NumberStatusChip value={data.status} />
        <QualityChip value={data.quality_rating} />
        {data.is_default ? <DefaultChip /> : null}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <HealthSection number={data} />
        <OverviewSection number={data} />
      </div>

      <div className="mt-4">
        <LinkedCampaignsSection number={data} />
      </div>
    </PageContainer>
  );
}

/**
 * Quality, tier, throughput and the platform's own verdict.
 *
 * Read from `/health`, which reports **stored** health — what the last sync wrote — and never calls
 * Meta, so it is available even when the channel is not. Refresh is what goes out and asks.
 */
function HealthSection({ number }: { number: PhoneNumber }): JSX.Element {
  const health = useNumberHealth(number.id);

  return (
    <Section title="Health">
      {health.isLoading ? (
        <Spinner label="Reading health…" />
      ) : health.isError ? (
        <ErrorState
          message={apiErrorMessage(health.error)}
          onRetry={() => void health.refetch()}
        />
      ) : health.data ? (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <HealthChip healthy={health.data.healthy} />
            <QualityChip value={health.data.quality_rating} />
          </div>

          {health.data.quality_rating && QUALITY_EXPLANATIONS[health.data.quality_rating] ? (
            <p
              className={`mb-3 rounded-md border px-3 py-2 text-sm ${
                health.data.quality_rating === "RED"
                  ? "border-danger text-danger"
                  : health.data.quality_rating === "YELLOW"
                    ? "border-warning text-warning"
                    : "border-border text-text-secondary"
              }`}
            >
              {QUALITY_EXPLANATIONS[health.data.quality_rating]}
            </p>
          ) : null}

          <dl>
            <DefinitionRow label="Messaging tier">
              <MetaValueChip value={health.data.messaging_tier} />
            </DefinitionRow>
            <DefinitionRow label="Throughput level">
              <MetaValueChip value={health.data.throughput_level} />
            </DefinitionRow>
            <DefinitionRow label="Send pacing">
              {formatCount(health.data.mps_limit)} messages/second
            </DefinitionRow>
            <DefinitionRow label="Connection status">
              <NumberStatusChip value={health.data.status} />
            </DefinitionRow>
            <DefinitionRow label="Last synced">
              {health.data.last_synced_at ? (
                <>
                  {formatDateTime(health.data.last_synced_at)}{" "}
                  <span className="text-text-disabled">
                    ({formatAge(health.data.last_synced_at)})
                  </span>
                </>
              ) : (
                "Never synced from Meta"
              )}
            </DefinitionRow>
          </dl>

          <p className="mt-3 text-xs text-text-disabled">
            These figures are what the last sync stored. Refresh re-pulls them from Meta; the tier
            and throughput values are Meta&apos;s own and are shown exactly as received.
          </p>
        </>
      ) : null}
    </Section>
  );
}

/** Identity, capability and ownership — what this number *is*, as opposed to how it is doing. */
function OverviewSection({ number }: { number: PhoneNumber }): JSX.Element {
  const waba = useWaba(number.waba_id);

  return (
    <Section title="Overview">
      <dl>
        <DefinitionRow label="Display number">{number.display_number}</DefinitionRow>
        <DefinitionRow label="Display name">{number.verified_name ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="Account">
          <Link to={`/channels/accounts/${number.waba_id}`} className="text-accent hover:underline">
            {waba.data?.business_name ?? number.waba_id}
          </Link>
        </DefinitionRow>
        <DefinitionRow label="Channel">
          <span className="font-mono text-xs">{number.channel_type}</span>
        </DefinitionRow>
        <DefinitionRow label="Default for sends">
          {number.is_default ? "Yes" : "No"}
        </DefinitionRow>
        <DefinitionRow label="Meta phone number id">
          <span className="break-all font-mono text-xs">{number.phone_number_id}</span>
        </DefinitionRow>
        <DefinitionRow label="Internal id">
          <span className="break-all font-mono text-xs">{number.id}</span>
        </DefinitionRow>
        <DefinitionRow label="Added">{formatDateTime(number.created_at)}</DefinitionRow>
      </dl>

      <p className="mt-3 text-xs text-text-disabled">
        The channel type is what makes this record portable beyond WhatsApp; every number here is a
        WhatsApp number today. Numbers arrive through a WABA sync and cannot be added or removed
        from the platform.
      </p>
    </Section>
  );
}

/** Campaigns pointed at this number — what would stop sending if it were suspended. */
function LinkedCampaignsSection({ number }: { number: PhoneNumber }): JSX.Element {
  const campaigns = useCampaigns();
  const mine = useMemo(
    () => (campaigns.data ?? []).filter((campaign) => campaign.phone_number_id === number.id),
    [campaigns.data, number.id],
  );

  return (
    <Section
      title="Campaigns using this number"
      action={
        <Link
          to="/campaigns"
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
        >
          Open campaigns
        </Link>
      }
    >
      {campaigns.isLoading ? (
        <Spinner label="Loading campaigns…" />
      ) : campaigns.isError ? (
        <ErrorState
          message={apiErrorMessage(campaigns.error)}
          onRetry={() => void campaigns.refetch()}
        />
      ) : mine.length === 0 ? (
        <EmptyState
          title="No campaigns use this number"
          description="Nothing would stop sending if this number were suspended."
        />
      ) : (
        <ul className="space-y-2">
          {mine.slice(0, 10).map((campaign) => (
            <li
              key={campaign.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border px-3 py-2"
            >
              <Link
                to={`/campaigns/${campaign.id}`}
                className="font-medium text-text-primary hover:text-accent"
              >
                {campaign.name}
              </Link>
              <span className="text-xs text-text-secondary">
                {campaign.status} · {formatCount(campaign.total_recipients)} recipients
              </span>
            </li>
          ))}
          {mine.length > 10 ? (
            <li className="text-xs text-text-disabled">
              and {formatCount(mine.length - 10)} more.
            </li>
          ) : null}
        </ul>
      )}
    </Section>
  );
}
