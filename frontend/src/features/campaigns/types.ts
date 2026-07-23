import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Campaign = components["schemas"]["CampaignResponse"];
export type CampaignList = components["schemas"]["CampaignListResponse"];
export type CampaignCreateRequest = components["schemas"]["CampaignCreateRequest"];
export type CampaignUpdateRequest = components["schemas"]["CampaignUpdateRequest"];
export type CampaignPreview = components["schemas"]["CampaignPreviewResponse"];
export type CampaignProgress = components["schemas"]["CampaignProgressResponse"];
export type CampaignState = components["schemas"]["CampaignStateResponse"];
export type CampaignDispatch = components["schemas"]["CampaignDispatchResponse"];
export type CampaignRetry = components["schemas"]["CampaignRetryResponse"];
export type CampaignEstimate = components["schemas"]["CampaignEstimateResponse"];
export type EstimateBreakdownEntry = components["schemas"]["EstimateBreakdownEntry"];
export type CampaignScheduleRequest = components["schemas"]["CampaignScheduleRequest"];
export type CampaignScheduleResult = components["schemas"]["CampaignScheduleResponse"];
export type ScheduleEntry = components["schemas"]["ScheduleEntry"];
export type RecipientEntry = components["schemas"]["RecipientEntry"];
export type RecipientsPage = components["schemas"]["RecipientsResponse"];
export type AudienceRef = components["schemas"]["AudienceRef"];
export type VariableMap = components["schemas"]["VariableMap"];

// Picker sources — the campaign wizard selects from these, it does not administer them.
export type Template = components["schemas"]["TemplateResponse"];
export type PhoneNumber = components["schemas"]["PhoneNumberResponse"];
export type Segment = components["schemas"]["SegmentResponse"];
export type Tag = components["schemas"]["TagResponse"];
export type AttributeDefinition = components["schemas"]["AttributeDefinitionResponse"];

/** The enums the contract *does* declare, taken from the request models rather than restated. */
export type AudienceType = CampaignCreateRequest["audience_type"];
export type ScheduleType = CampaignScheduleRequest["schedule_type"];

/**
 * Campaign and recipient status are typed `str` on the wire (Doc 04 §17), so the contract carries
 * no enum to derive from. These are the **display vocabulary** for the values Doc 03 §8.1/§8.3
 * define — labels and a filter list, not an API type. Any value the server sends that is missing
 * here renders verbatim rather than being dropped, so an added status degrades gracefully.
 */
export const CAMPAIGN_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  queued: "Queued",
  running: "Running",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
  failed: "Failed",
};

export const CAMPAIGN_STATUSES: string[] = Object.keys(CAMPAIGN_STATUS_LABELS);

export const RECIPIENT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  queued: "Queued",
  sent: "Sent",
  delivered: "Delivered",
  read: "Read",
  failed: "Failed",
  skipped: "Skipped",
  cancelled: "Cancelled",
};

export const RECIPIENT_STATUSES: string[] = Object.keys(RECIPIENT_STATUS_LABELS);

export const AUDIENCE_TYPE_LABELS: Record<AudienceType, string> = {
  segment: "Segment",
  tag: "Tags",
  list: "Selected contacts",
  upload: "Uploaded list",
};

export const SCHEDULE_TYPE_LABELS: Record<ScheduleType, string> = {
  one_time: "One-time",
  recurring: "Recurring",
  drip: "Drip sequence",
};

// --- Lifecycle rules, mirrored from the server so the UI offers only what will be accepted ------
//
// The server remains the authority (Doc 04 §17 answers 409 on a bad transition, and that error is
// surfaced verbatim). These predicates exist so an action that *cannot* succeed is not offered in
// the first place — they gate presentation, never correctness.

/** `CAMPAIGN_EDITABLE` — only a draft is still owned by the operator (models/campaign.py). */
export function isEditable(campaign: Campaign): boolean {
  return campaign.status === "draft";
}

/** `CAMPAIGN_DISPATCHABLE` — nothing may be in flight when a dispatch starts. */
export function isDispatchable(campaign: Campaign): boolean {
  return campaign.status === "draft" || campaign.status === "scheduled";
}

/** `CAMPAIGN_SENDING` — the states a pause acts on. */
export function isPausable(campaign: Campaign): boolean {
  return campaign.status === "queued" || campaign.status === "running";
}

export function isResumable(campaign: Campaign): boolean {
  return campaign.status === "paused";
}

/** `CAMPAIGN_TERMINAL` — nothing more will ever be sent from these. */
export function isTerminal(campaign: Campaign): boolean {
  return (
    campaign.status === "completed" ||
    campaign.status === "cancelled" ||
    campaign.status === "failed"
  );
}

export function isCancellable(campaign: Campaign): boolean {
  return !isTerminal(campaign);
}

/** A retry needs failed recipients and a campaign that was not cancelled. */
export function isRetryable(campaign: Campaign): boolean {
  return campaign.status !== "cancelled" && campaign.failed_count > 0;
}

/** Scheduling parks the campaign in `scheduled`; only a not-yet-flying campaign may be parked. */
export function isSchedulable(campaign: Campaign): boolean {
  return isDispatchable(campaign);
}

// --- List query (client-side; see `api.ts` for why) ---------------------------------------------

export type CampaignSort = "-created_at" | "created_at" | "name" | "-name" | "-total_recipients";

export interface CampaignListQuery {
  q: string;
  status: string;
  sort: CampaignSort;
  page: number;
}

export const DEFAULT_LIST_QUERY: CampaignListQuery = {
  q: "",
  status: "",
  sort: "-created_at",
  page: 1,
};
