import { Link, useLocation } from "react-router-dom";

import { ManagePageHeader } from "@/components/layout";
import { CampaignWizard } from "@/features/campaigns/CampaignWizard";
import {
  contactsToForm,
  duplicateToForm,
  followUpToForm,
} from "@/features/campaigns/campaignForm";
import type { Campaign } from "@/features/campaigns/types";

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
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader
        title={
          followUp
            ? `Follow up "${source?.name ?? "campaign"}"`
            : source
              ? `Duplicate "${source.name}"`
              : "Create Campaign"
        }
        actions={
          <Link to="/campaigns" className="text-sm font-medium text-[var(--color-nav-bg)] hover:underline dark:text-accent">
            Back to campaigns
          </Link>
        }
      />
      <div className="px-4 py-6 sm:px-[30px]">
      <p className="mx-auto mb-4 max-w-5xl text-sm text-[#6e6e6e] dark:text-text-secondary">
        {followUp
          ? "The original definition is ready to review as a new draft. You can change its audience, message and timing before approval."
          : "Choose who gets it, pick an approved template, then send now or schedule it. Nothing is sent until you confirm."}
      </p>
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
      </div>
    </div>
  );
}
