import type { Campaign, CampaignListQuery, CampaignSort } from "@/features/campaigns/types";

/** Rows per page for the client-side list (see `useCampaigns` for why paging lives here). */
export const PAGE_SIZE = 25;

function byName(a: Campaign, b: Campaign): number {
  return a.name.localeCompare(b.name);
}

function byCreated(a: Campaign, b: Campaign): number {
  return Date.parse(a.created_at) - Date.parse(b.created_at);
}

const COMPARATORS: Record<CampaignSort, (a: Campaign, b: Campaign) => number> = {
  "-created_at": (a, b) => byCreated(b, a),
  created_at: byCreated,
  name: byName,
  "-name": (a, b) => byName(b, a),
  "-total_recipients": (a, b) => b.total_recipients - a.total_recipients,
};

/** Case-insensitive name match — the same field the server's `q` filters on (`Campaign.name`). */
export function matchesSearch(campaign: Campaign, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return campaign.name.toLowerCase().includes(needle);
}

export function filterCampaigns(campaigns: Campaign[], query: CampaignListQuery): Campaign[] {
  return campaigns.filter(
    (campaign) =>
      matchesSearch(campaign, query.q) &&
      (query.status === "" || campaign.status === query.status),
  );
}

export function sortCampaigns(campaigns: Campaign[], sort: CampaignSort): Campaign[] {
  return [...campaigns].sort(COMPARATORS[sort]);
}

export interface CampaignPage {
  rows: Campaign[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, in that order, so the page numbers describe the filtered set. */
export function selectCampaignPage(
  campaigns: Campaign[],
  query: CampaignListQuery,
): CampaignPage {
  const matched = sortCampaigns(filterCampaigns(campaigns, query), query.sort);
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * PAGE_SIZE;
  return {
    rows: matched.slice(start, start + PAGE_SIZE),
    total: matched.length,
    totalPages,
    page,
  };
}

// --- Delivery statistics ------------------------------------------------------------------------

/**
 * A rate over the campaign's own denominator, or `null` when there is nothing to divide by.
 *
 * `null` means *unknown*, not zero — the same discipline the analytics module applies (Doc 15 §11).
 */
export function rate(numerator: number, denominator: number): number | null {
  if (denominator <= 0) return null;
  return numerator / denominator;
}

export interface DeliveryStats {
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  replied: number;
  total: number;
  deliveryRate: number | null;
  readRate: number | null;
  failureRate: number | null;
  replyRate: number | null;
}

/**
 * Delivery statistics from the campaign's own counters.
 *
 * Denominators follow the funnel rather than the total: delivery is measured against what was
 * actually sent, and read against what was actually delivered, so a campaign still fanning out is
 * not reported as failing simply because most of its roster has not left the queue yet.
 */
export function deliveryStats(campaign: Campaign): DeliveryStats {
  return {
    sent: campaign.sent_count,
    delivered: campaign.delivered_count,
    read: campaign.read_count,
    failed: campaign.failed_count,
    replied: campaign.replied_count,
    total: campaign.total_recipients,
    deliveryRate: rate(campaign.delivered_count, campaign.sent_count),
    readRate: rate(campaign.read_count, campaign.delivered_count),
    failureRate: rate(campaign.failed_count, campaign.total_recipients),
    replyRate: rate(campaign.replied_count, campaign.delivered_count),
  };
}

/**
 * How far through the roster the campaign is, 0–1.
 *
 * Everything that has left the queue counts as handled — sent, failed and read alike — because
 * progress asks "how much is left to do", and a failed recipient is done being attempted.
 */
export function completionRatio(campaign: Campaign): number | null {
  if (campaign.total_recipients <= 0) return null;
  const handled = campaign.sent_count + campaign.failed_count;
  return Math.min(1, handled / campaign.total_recipients);
}
