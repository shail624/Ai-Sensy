import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { AnalyticsDashboard } from "@/features/analytics";

/** Route page for Analytics & Reporting (Doc 15, Phase 8). */
export function AnalyticsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Analytics" }]} />
      <PageHeader
        eyebrow="Performance intelligence"
        title="Analytics"
        description="Delivery, campaigns, conversations and follow-up — from the rollups."
      />
      <AnalyticsDashboard />
    </PageContainer>
  );
}
