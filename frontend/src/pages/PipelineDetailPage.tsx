import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { PipelineDetail } from "@/features/pipelines";

/** Route page: resolves the pipeline id from the URL and renders the detail surface. */
export function PipelineDetailPage(): JSX.Element {
  const { pipelineId } = useParams<{ pipelineId: string }>();

  if (!pipelineId) {
    return (
      <PageContainer>
        <EmptyState title="No pipeline selected" />
      </PageContainer>
    );
  }
  return <PipelineDetail pipelineId={pipelineId} />;
}
