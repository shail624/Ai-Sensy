import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState } from "@/components/ui";

/** Placeholder page for modules that are not built yet. No business logic. */
export function ComingSoonPage({ title }: { title: string }): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: title }]} />
      <PageHeader title={title} />
      <EmptyState
        title={`${title} is coming soon`}
        description="This module has not been built yet."
      />
    </PageContainer>
  );
}
