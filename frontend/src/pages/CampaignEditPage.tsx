import { Link, useParams } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { CampaignWizard } from "@/features/campaigns/CampaignWizard";
import { campaignToForm } from "@/features/campaigns/campaignForm";
import { apiErrorMessage, useCampaign } from "@/features/campaigns/api";
import { isEditable } from "@/features/campaigns/types";

/**
 * Route page for editing a campaign's definition.
 *
 * Only a draft is still the operator's to change — once a campaign has been handed to the send
 * fabric, editing it would change what is already in flight, and the server answers 409. That is
 * said here rather than discovered on save.
 */
export function CampaignEditPage(): JSX.Element {
  const { campaignId } = useParams<{ campaignId: string }>();
  const campaign = useCampaign(campaignId ?? "", Boolean(campaignId));

  if (!campaignId) {
    return (
      <PageContainer>
        <EmptyState title="No campaign selected" />
      </PageContainer>
    );
  }

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
      <Breadcrumbs
        items={[
          { label: "Campaigns", to: "/campaigns" },
          { label: data.name, to: `/campaigns/${data.id}` },
          { label: "Edit" },
        ]}
      />
      <PageHeader eyebrow="Campaign builder" title={`Edit "${data.name}"`} />

      {isEditable(data) ? (
        <CampaignWizard campaign={data} initialValues={campaignToForm(data)} />
      ) : (
        <>
          <EmptyState
            title="This campaign can no longer be edited"
            description={`It is ${data.status}. Editing would change what is already in flight — duplicate it instead to start a new draft from the same definition.`}
          />
          <div className="mt-3 text-center">
            <Link to={`/campaigns/${data.id}`} className="text-sm text-accent hover:underline">
              Back to the campaign
            </Link>
          </div>
        </>
      )}
    </PageContainer>
  );
}
