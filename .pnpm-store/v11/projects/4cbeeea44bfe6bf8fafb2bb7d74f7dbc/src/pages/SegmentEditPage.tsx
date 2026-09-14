import { useParams } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { SegmentEditor } from "@/features/segments";
import { apiErrorMessage, useSegment } from "@/features/segments/api";

/**
 * Route page for editing a segment.
 *
 * Any segment can be edited — the backend applies no state guard and no version check, so the last
 * write wins. Saving replaces the rule set wholesale and clears the cached size.
 */
export function SegmentEditPage(): JSX.Element {
  const { segmentId } = useParams<{ segmentId: string }>();
  const segment = useSegment(segmentId ?? "", Boolean(segmentId));

  if (!segmentId) {
    return (
      <PageContainer>
        <EmptyState title="No segment selected" />
      </PageContainer>
    );
  }

  if (segment.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading segment…" />
      </PageContainer>
    );
  }

  if (segment.isError || !segment.data) {
    return (
      <PageContainer>
        <ErrorState message={apiErrorMessage(segment.error)} onRetry={() => void segment.refetch()} />
      </PageContainer>
    );
  }

  const data = segment.data;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Segments", to: "/segments" },
          { label: data.name, to: `/segments/${data.id}` },
          { label: "Edit" },
        ]}
      />
      <PageHeader title={`Edit "${data.name}"`} />
      <SegmentEditor segment={data} />
    </PageContainer>
  );
}
