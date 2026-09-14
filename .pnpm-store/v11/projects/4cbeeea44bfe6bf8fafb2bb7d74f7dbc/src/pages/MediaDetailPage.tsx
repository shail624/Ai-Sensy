import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { MediaDetail } from "@/features/media";

/** Route page: resolves the media id from the URL and renders the detail surface. */
export function MediaDetailPage(): JSX.Element {
  const { mediaId } = useParams<{ mediaId: string }>();

  if (!mediaId) {
    return (
      <PageContainer>
        <EmptyState title="No file selected" />
      </PageContainer>
    );
  }
  return <MediaDetail mediaId={mediaId} />;
}
