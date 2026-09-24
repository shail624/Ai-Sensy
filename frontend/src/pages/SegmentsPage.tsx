import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { AudiencePresetGallery, SegmentList } from "@/features/segments";
import { AiFoundationPanel } from "@/features/ai";

/** Route page for the Segments module (FR-CON-10). */
export function SegmentsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Segments" }]} />
      <PageHeader
        title="Segments"
        description="Saved groups of contacts. A campaign uses the latest members when it sends."
      />
      <div className="mb-5">
        <AiFoundationPanel compact capabilities={["audience"]} context="existing contact attributes and reusable segment rules" />
      </div>
      <AudiencePresetGallery />
      <SegmentList />
    </PageContainer>
  );
}
