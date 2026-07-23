import { Link, useParams } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { draftFromTemplate, TemplateEditor } from "@/features/templates";
import { apiErrorMessage, useTemplate } from "@/features/templates/api";
import { isEditable, STATUS_LABELS } from "@/features/templates/types";

/**
 * Route page for editing a template's definition.
 *
 * Only a `draft` or `rejected` template is still the platform's to change — once Meta owns it, an
 * edit would be overwritten by the next sync, and the server answers 409. That is said here rather
 * than discovered on save, with the clone route offered as the thing to do instead.
 */
export function TemplateEditPage(): JSX.Element {
  const { templateId } = useParams<{ templateId: string }>();
  const template = useTemplate(templateId ?? "", Boolean(templateId));

  if (!templateId) {
    return (
      <PageContainer>
        <EmptyState title="No template selected" />
      </PageContainer>
    );
  }

  if (template.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading template…" />
      </PageContainer>
    );
  }

  if (template.isError || !template.data) {
    return (
      <PageContainer>
        <ErrorState
          message={apiErrorMessage(template.error)}
          onRetry={() => void template.refetch()}
        />
      </PageContainer>
    );
  }

  const data = template.data;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Templates", to: "/templates" },
          { label: data.name, to: `/templates/${data.id}` },
          { label: "Edit" },
        ]}
      />
      <PageHeader title={`Edit "${data.name}"`} />

      {isEditable(data) ? (
        <TemplateEditor template={data} initialDraft={draftFromTemplate(data)} />
      ) : (
        <>
          <EmptyState
            title="This template can no longer be edited"
            description={`It is ${(STATUS_LABELS[data.status] ?? data.status).toLowerCase()} — Meta owns it now, and an edit here would be overwritten by the next sync. Clone it to start a new template from the same definition.`}
          />
          <div className="mt-3 flex justify-center gap-3 text-sm">
            <Link to={`/templates/${data.id}`} className="text-accent hover:underline">
              Back to the template
            </Link>
          </div>
        </>
      )}
    </PageContainer>
  );
}
