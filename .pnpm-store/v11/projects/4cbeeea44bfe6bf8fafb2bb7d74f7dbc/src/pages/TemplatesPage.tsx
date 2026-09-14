import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { TemplateList } from "@/features/templates";

/** Route page for the Templates module (Doc 05 B5.1). */
export function TemplatesPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Templates" }]} />
      <PageHeader
        eyebrow="Reusable content"
        title="Template Center"
        description="Search, filter, preview, favorite, version, and govern every WhatsApp template from one registry."
      />
      <TemplateList />
    </PageContainer>
  );
}
