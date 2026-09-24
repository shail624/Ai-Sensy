import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { PipelineList } from "@/features/pipelines";

/** Route page for the Lead Pipelines module (Doc 07 §19). */
export function PipelinesPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Pipelines" }]} />
      <PageHeader
        title="Lead pipelines"
        description="The steps a lead goes through. You move leads between steps from Live Chat."
      />
      <PipelineList />
    </PageContainer>
  );
}
