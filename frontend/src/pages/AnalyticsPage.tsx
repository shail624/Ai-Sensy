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
        description="How your messages, campaigns and chats are doing."
      />
      <AnalyticsDashboard />
    </PageContainer>
  );
}
