import { useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { CampaignWizard, duplicateToForm } from "@/features/campaigns";
import type { Campaign } from "@/features/campaigns";

/**
 * Route page for creating a campaign — and for duplicating one.
 *
 * A duplicate arrives as router state carrying the source campaign, so the wizard opens prefilled
 * with its definition under a new name. Nothing is copied server-side: the result is an ordinary
 * new draft, created by the same POST as any other.
 */
export function CampaignCreatePage(): JSX.Element {
  const location = useLocation();
  const source = (location.state as { duplicateOf?: Campaign } | null)?.duplicateOf;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Campaigns", to: "/campaigns" },
          { label: source ? "Duplicate campaign" : "New campaign" },
        ]}
      />
      <PageHeader
        title={source ? `Duplicate "${source.name}"` : "New campaign"}
        description="Choose the message, the audience and when it goes out. Nothing is sent until you say so."
      />
      <CampaignWizard initialValues={source ? duplicateToForm(source) : undefined} />
    </PageContainer>
  );
}
