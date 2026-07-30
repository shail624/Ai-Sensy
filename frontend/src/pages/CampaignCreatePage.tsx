import { Sparkles } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import {
  CampaignWizard,
  contactsToForm,
  duplicateToForm,
  followUpToForm,
} from "@/features/campaigns";
import { AiFoundationPanel } from "@/features/ai";
import type { Campaign } from "@/features/campaigns";

/**
 * Route page for creating a campaign — and for duplicating one.
 *
 * A duplicate arrives as router state carrying the source campaign, so the wizard opens prefilled
 * with its definition under a new name. Nothing is copied server-side: the result is an ordinary
 * new draft, created by the same POST as any other.
 */
export function CampaignCreatePage(): JSX.Element {
  const location = useLocation();
  const state = location.state as {
    duplicateOf?: Campaign;
    contactIds?: string[];
    intent?: "duplicate" | "follow_up";
  } | null;
  const source = state?.duplicateOf;
  const followUp = Boolean(source && state?.intent === "follow_up");
  // A selection handed over from the contacts list opens the wizard on a `list` audience.
  const contactIds = state?.contactIds;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Campaigns", to: "/campaigns" },
          { label: followUp ? "Follow-up campaign" : source ? "Duplicate campaign" : "New campaign" },
        ]}
      />
      <PageHeader
        eyebrow="Campaign builder"
        title={
          followUp
            ? `Follow up "${source?.name ?? "campaign"}"`
            : source
              ? `Duplicate "${source.name}"`
              : "New campaign"
        }
        description={
          followUp
            ? "The original definition is ready to review as a new draft. You can change its audience, message and timing before approval."
            : "Choose the message, the audience and when it goes out. Nothing is sent until you say so."
        }
      />
      <details className="group mx-auto mb-4 max-w-5xl rounded-xl border border-border bg-surface">
        <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
          <span className="flex items-center gap-2">
            <Sparkles aria-hidden className="h-4 w-4 text-accent" />
            AI planning assistant
            <span className="font-normal text-text-disabled">Optional</span>
          </span>
          <span className="text-xs font-medium text-accent group-open:hidden">Show</span>
          <span className="hidden text-xs font-medium text-accent group-open:inline">Hide</span>
        </summary>
        <div className="border-t border-border p-2">
          <AiFoundationPanel
            compact
            capabilities={["campaign", "audience"]}
            context="the campaign objective and selected audience"
          />
        </div>
      </details>
      <CampaignWizard
        initialValues={
          source
            ? followUp
              ? followUpToForm(source)
              : duplicateToForm(source)
            : contactIds?.length
              ? contactsToForm(contactIds)
              : undefined
        }
      />
    </PageContainer>
  );
}
