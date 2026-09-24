import { ManagePageHeader } from "@/components/layout";
import { CampaignList } from "@/features/campaigns";
import { QuickGuide } from "@/features/settings/QuickGuide";

/** Route page for the Campaigns module (Doc 05 B4.1), laid out as the reference page. */
export function CampaignsPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Campaigns" />
      <div className="space-y-4 px-4 py-6 sm:px-[30px]">
        <QuickGuide
          eyebrow="Campaigns quick guide"
          text="Launch a broadcast: choose who gets it (a segment, tags or a list), pick an approved template, then send now or schedule it. Open a campaign to see who received and read it."
        />
        <CampaignList />
      </div>
    </div>
  );
}
