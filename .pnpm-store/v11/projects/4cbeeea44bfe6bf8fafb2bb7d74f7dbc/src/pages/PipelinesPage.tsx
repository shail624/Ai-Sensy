import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { PipelineList } from "@/features/pipelines";

/** Route page for the Lead Pipelines module (Doc 07 §19). */
export function PipelinesPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Pipelines" }]} />
      <PageHeader
        title="Lead pipelines"
        description="The ordered stages a lead moves through. Configuration only — leads are moved from the Inbox."
      />
      <PipelineList />
    </PageContainer>
  );
}
