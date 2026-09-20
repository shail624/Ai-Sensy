import { Sparkles } from "lucide-react";
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
      <details className="group mx-auto mb-4 max-w-7xl rounded-xl border border-border bg-surface">
        <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
          <span className="flex items-center gap-2">
            <Sparkles aria-hidden className="h-4 w-4 text-accent" />
            AI template assistant
            <span className="font-normal text-text-disabled">Optional</span>
          </span>
          <span className="text-xs font-medium text-accent group-open:hidden">Show</span>
          <span className="hidden text-xs font-medium text-accent group-open:inline">Hide</span>
        </summary>
        <div className="border-t border-border p-2">
          <AiFoundationPanel
            compact
            capabilities={["template"]}
            context="the template category, language, and compliance constraints"
          />
        </div>
      </details>
      <TemplateEditor initialDraft={source ? cloneDraft(source) : undefined} />
    </PageContainer>
  );
}
