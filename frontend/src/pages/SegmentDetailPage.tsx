import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { SegmentDetail } from "@/features/segments";

/** Route page: resolves the segment id from the URL and renders the detail surface. */
export function SegmentDetailPage(): JSX.Element {
  const { segmentId } = useParams<{ segmentId: string }>();

  if (!segmentId) {
    return (
      <PageContainer>
        <EmptyState title="No segment selected" />
      </PageContainer>
    );
  }
  return <SegmentDetail segmentId={segmentId} />;
}
