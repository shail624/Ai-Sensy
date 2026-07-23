import { useParams } from "react-router-dom";

import { PageContainer } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { TemplateDetail } from "@/features/templates";

/** Route page: resolves the template id from the URL and renders the detail surface. */
export function TemplateDetailPage(): JSX.Element {
  const { templateId } = useParams<{ templateId: string }>();

  if (!templateId) {
    return (
      <PageContainer>
        <EmptyState title="No template selected" />
      </PageContainer>
    );
  }
  return <TemplateDetail templateId={templateId} />;
}
