import { useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { cloneDraft, TemplateEditor } from "@/features/templates";
import { AiFoundationPanel } from "@/features/ai";
import type { Template } from "@/features/templates";

/**
 * Route page for creating a template — and for cloning one.
 *
 * A clone arrives as router state carrying the source template, so the editor opens prefilled with
 * its definition under a new name. Nothing is copied server-side: the result is an ordinary new
 * template, created by the same POST as any other. Cloning is how an operator changes an approved
 * template, which Meta will not let them edit in place.
 */
export function TemplateCreatePage(): JSX.Element {
  const location = useLocation();
  const source = (location.state as { cloneOf?: Template } | null)?.cloneOf;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Templates", to: "/templates" },
          { label: source ? "Clone template" : "New template" },
        ]}
      />
      <PageHeader
        title={source ? `Clone "${source.name}"` : "New template"}
        description="Build the message, then save it as a draft or submit it to Meta for review."
      />
      <div className="mb-5">
        <AiFoundationPanel compact capabilities={["template"]} context="the template category, language, and compliance constraints" />
      </div>
      <TemplateEditor initialDraft={source ? cloneDraft(source) : undefined} />
    </PageContainer>
  );
}
