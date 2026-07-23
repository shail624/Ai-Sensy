import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { SegmentList } from "@/features/segments";

/** Route page for the Segments module (FR-CON-10). */
export function SegmentsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Segments" }]} />
      <PageHeader
        title="Segments"
        description="Saved filters over your contacts. Campaigns resolve them live at dispatch."
      />
      <SegmentList />
    </PageContainer>
  );
}
