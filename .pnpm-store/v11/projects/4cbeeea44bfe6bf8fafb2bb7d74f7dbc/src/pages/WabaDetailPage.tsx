import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { WabaDetail } from "@/features/channels";

/** Route page: resolves the account id from the URL and renders the detail surface. */
export function WabaDetailPage(): JSX.Element {
  const { wabaId } = useParams<{ wabaId: string }>();

  if (!wabaId) {
    return (
      <PageContainer>
        <EmptyState title="No account selected" />
      </PageContainer>
    );
  }
  return <WabaDetail wabaId={wabaId} />;
}
