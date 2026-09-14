import { Link } from "react-router-dom";

import { CampaignActions } from "@/features/campaigns/CampaignActions";
import {
  AudienceChip,
  CampaignProgressBar,
  CampaignStatusChip,
} from "@/features/campaigns/CampaignBadges";
import { formatCount, formatDate } from "@/features/campaigns/format";
import type { Campaign } from "@/features/campaigns/types";

interface Props {
  campaigns: Campaign[];
}

/**
 * The campaign list table (Doc 05 B4.1). Rows compose the same badge and action components the
 * detail page uses, so a campaign reads and behaves identically on both surfaces.
 *
 * Secondary columns drop away below `md` rather than being squeezed: name, status and actions are
 * what the list is for, and the rest is one tap away on the detail page.
 */
export function CampaignTable({ campaigns }: Props): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="px-3 py-2">Campaign</th>
            <th scope="col" className="px-3 py-2">Status</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Audience</th>
            <th scope="col" className="hidden px-3 py-2 md:table-cell">Recipients</th>
            <th scope="col" className="hidden px-3 py-2 md:table-cell">Progress</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Created</th>
            <th scope="col" className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((campaign) => (
            <tr key={campaign.id} className="border-b border-border last:border-0 hover:bg-hover">
              <td className="px-3 py-2">
                <Link
                  to={`/campaigns/${campaign.id}`}
                  className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  {campaign.name}
                </Link>
                <div className="mt-1 lg:hidden">
                  <AudienceChip value={campaign.audience_type} />
                </div>
              </td>
              <td className="px-3 py-2">
                <CampaignStatusChip value={campaign.status} />
              </td>
              <td className="hidden px-3 py-2 lg:table-cell">
                <AudienceChip value={campaign.audience_type} />
              </td>
              <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                {formatCount(campaign.total_recipients)}
              </td>
              <td className="hidden px-3 py-2 md:table-cell">
                <CampaignProgressBar campaign={campaign} compact />
              </td>
              <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                {formatDate(campaign.created_at)}
              </td>
              <td className="px-3 py-2">
                <CampaignActions campaign={campaign} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
