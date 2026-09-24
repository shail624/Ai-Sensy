import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { CampaignList } from "@/features/campaigns";

/** Route page for the Campaigns module (Doc 05 B4.1). */
export function CampaignsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Campaigns" }]} />
      <PageHeader
        eyebrow="Engagement orchestration"
        title="Campaigns"
        description="Create, schedule and track your WhatsApp campaigns."
      />
      <CampaignList />
    </PageContainer>
  );
}
