import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { JobDetail } from "@/features/operations";

/** Route page: resolves the job id from the URL and renders the detail surface. */
export function JobDetailPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();

  if (!jobId) {
    return (
      <PageContainer>
        <EmptyState title="No job selected" />
      </PageContainer>
    );
  }
  return <JobDetail jobId={jobId} />;
}
