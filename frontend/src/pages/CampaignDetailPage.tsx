import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { CampaignDetail } from "@/features/campaigns";

/** Route page: resolves the campaign id from the URL and renders the detail surface. */
export function CampaignDetailPage(): JSX.Element {
  const { campaignId } = useParams<{ campaignId: string }>();

  if (!campaignId) {
    return (
      <PageContainer>
        <EmptyState title="No campaign selected" />
      </PageContainer>
    );
  }
  return <CampaignDetail campaignId={campaignId} />;
}
