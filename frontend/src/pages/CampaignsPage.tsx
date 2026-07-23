import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { CampaignList } from "@/features/campaigns";

/** Route page for the Campaigns module (Doc 05 B4.1). */
export function CampaignsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Campaigns" }]} />
      <PageHeader
        title="Campaigns"
        description="Broadcast an approved template to a segment, a set of tags, or a list of contacts."
      />
      <CampaignList />
    </PageContainer>
  );
}
