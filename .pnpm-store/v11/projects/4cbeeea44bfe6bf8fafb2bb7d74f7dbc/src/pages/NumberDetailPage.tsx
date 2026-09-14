import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { NumberDetail } from "@/features/channels";

/** Route page: resolves the number id from the URL and renders the detail surface. */
export function NumberDetailPage(): JSX.Element {
  const { numberId } = useParams<{ numberId: string }>();

  if (!numberId) {
    return (
      <PageContainer>
        <EmptyState title="No number selected" />
      </PageContainer>
    );
  }
  return <NumberDetail numberId={numberId} />;
}
