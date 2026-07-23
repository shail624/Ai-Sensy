import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { TemplateList } from "@/features/templates";

/** Route page for the Templates module (Doc 05 B5.1). */
export function TemplatesPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Templates" }]} />
      <PageHeader
        title="Templates"
        description="Message templates and their approval status. Only an approved template can be broadcast."
      />
      <TemplateList />
    </PageContainer>
  );
}
