import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useCampaign,
  useCampaignProgress,
  usePhoneNumbers,
  useSegments,
  useTags,
  useTemplates,
} from "@/features/campaigns/api";
import { CampaignActions } from "@/features/campaigns/CampaignActions";
import { AudienceChip, CampaignStatusChip } from "@/features/campaigns/CampaignBadges";
import { CampaignPreviewPanel } from "@/features/campaigns/CampaignPreviewPanel";
import { CampaignRecipients } from "@/features/campaigns/CampaignRecipients";
import { CampaignScheduleDialog } from "@/features/campaigns/CampaignScheduleDialog";
import { CampaignStats } from "@/features/campaigns/CampaignStats";
import { CampaignTimeline } from "@/features/campaigns/CampaignTimeline";
import { formatCount, formatDateTime } from "@/features/campaigns/format";
import type { Campaign } from "@/features/campaigns/types";
import { AUDIENCE_TYPE_LABELS, isTerminal } from "@/features/campaigns/types";

const TABS = ["overview", "recipients", "cost", "timeline"] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  overview: "Overview",
  recipients: "Recipients",
  cost: "Preview & cost",
  timeline: "Timeline",
};

/**
 * The campaign detail surface (Doc 05 B4.3) — definition, live progress, delivery statistics, the
 * per-recipient ledger, audience preview, cost and lifecycle, with the action set in the header.
 */
export function CampaignDetail({ campaignId }: { campaignId: string }): JSX.Element {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("overview");
  const [scheduling, setScheduling] = useState(false);

  const campaign = useCampaign(campaignId);
  // A finished campaign's numbers never change again, so it is read once rather than polled.
  const live = campaign.data !== undefined && !isTerminal(campaign.data);
  const progress = useCampaignProgress(campaignId, live);

  if (campaign.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading campaign…" />
      </PageContainer>
    );
  }

  if (campaign.isError || !campaign.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Campaigns", to: "/campaigns" }, { label: "Campaign" }]} />
        <ErrorState
          message={apiErrorMessage(campaign.error)}
          onRetry={() => void campaign.refetch()}
        />
      </PageContainer>
    );
  }

  const data = campaign.data;

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Campaigns", to: "/campaigns" }, { label: data.name }]} />
      <PageHeader
        title={data.name}
        description={`${formatCount(data.total_recipients)} recipients · created ${formatDateTime(
          data.created_at,
        )}`}
        actions={
          <CampaignActions
            campaign={data}
            onDeleted={() => navigate("/campaigns")}
            onSchedule={() => setScheduling(true)}
          />
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <CampaignStatusChip value={data.status} />
        <AudienceChip value={data.audience_type} />
      </div>

      <nav aria-label="Campaign sections" className="mb-4 flex flex-wrap gap-2">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            aria-current={tab === key ? "page" : undefined}
            className={`rounded-md border px-3 py-1 text-sm ${
              tab === key
                ? "border-accent text-accent"
                : "border-border text-text-secondary hover:bg-hover"
            }`}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </nav>

      {tab === "overview" ? (
        <div className="space-y-4">
          <CampaignDefinition campaign={data} />
          <CampaignStats
            campaign={data}
            progress={progress.data}
            live={live}
            isLoadingProgress={progress.isLoading}
          />
        </div>
      ) : null}

      {tab === "recipients" ? <CampaignRecipients campaignId={campaignId} /> : null}
      {tab === "cost" ? <CampaignPreviewPanel campaignId={campaignId} /> : null}
      {tab === "timeline" ? (
        <CampaignTimeline campaign={data} progress={progress.data} />
      ) : null}

      {scheduling ? (
        <CampaignScheduleDialog campaign={data} onClose={() => setScheduling(false)} />
      ) : null}
    </PageContainer>
  );
}

/** What the campaign is: message, sender and audience, resolved to names rather than ids. */
function CampaignDefinition({ campaign }: { campaign: Campaign }): JSX.Element {
  const numbers = usePhoneNumbers();
  const templates = useTemplates();
  const segments = useSegments(campaign.audience_type === "segment");
  const tags = useTags(campaign.audience_type === "tag");

  const ref = (campaign.audience_ref ?? {}) as Record<string, unknown>;
  const number = numbers.data?.find((candidate) => candidate.id === campaign.phone_number_id);
  const template = templates.data?.find((candidate) => candidate.id === campaign.template_id);
  const segment = segments.data?.find(
    (candidate) => candidate.id === (typeof ref.segment_id === "string" ? ref.segment_id : ""),
  );
  const tagIds = Array.isArray(ref.tag_ids) ? ref.tag_ids : [];
  const selectedTags = (tags.data ?? []).filter((tag) => tagIds.includes(tag.id));
  const contactIds = Array.isArray(ref.contact_ids) ? ref.contact_ids : [];

  return (
    <Section title="Definition">
      <dl>
        <DefinitionRow label="Status">
          <CampaignStatusChip value={campaign.status} />
        </DefinitionRow>
        <DefinitionRow label="Send from">
          {number
            ? `${number.display_number}${number.verified_name ? ` — ${number.verified_name}` : ""}`
            : campaign.phone_number_id}
        </DefinitionRow>
        <DefinitionRow label="Template">
          {template ? `${template.name} (${template.language}) — ${template.category}` : campaign.template_id}
        </DefinitionRow>
        <DefinitionRow label="Audience">
          {AUDIENCE_TYPE_LABELS[campaign.audience_type as keyof typeof AUDIENCE_TYPE_LABELS] ??
            campaign.audience_type}
          {segment ? ` — ${segment.name}` : ""}
          {selectedTags.length > 0 ? ` — ${selectedTags.map((tag) => tag.name).join(", ")}` : ""}
          {campaign.audience_type === "list" ? ` — ${formatCount(contactIds.length)} contacts` : ""}
        </DefinitionRow>
        <DefinitionRow label="Created">{formatDateTime(campaign.created_at)}</DefinitionRow>
        <DefinitionRow label="Last updated">{formatDateTime(campaign.updated_at)}</DefinitionRow>
      </dl>
    </Section>
  );
}
