import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Template = components["schemas"]["TemplateResponse"];
export type TemplateList = components["schemas"]["TemplateListResponse"];
export type TemplateCreateRequest = components["schemas"]["TemplateCreateRequest"];
export type TemplateUpdateRequest = components["schemas"]["TemplateUpdateRequest"];
export type TemplatePreview = components["schemas"]["TemplatePreviewResponse"];
export type TemplateVersion = components["schemas"]["TemplateVersionEntry"];
export type TemplateVersions = components["schemas"]["TemplateVersionsResponse"];
export type JobAccepted = components["schemas"]["JobAcceptedResponse"];

/** Picker source — the create form selects a WABA; it does not administer one. */
export type Waba = components["schemas"]["WabaResponse"];

/** The one template enum the contract declares, taken from the request model. */
export type Category = NonNullable<TemplateCreateRequest["category"]>;

export const CATEGORY_LABELS: Record<Category, string> = {
  marketing: "Marketing",
  utility: "Utility",
  authentication: "Authentication",
};

export const CATEGORIES = Object.keys(CATEGORY_LABELS) as Category[];

/**
 * Approval status is typed `str` on the wire (Doc 04 §15), so there is no enum to derive from.
 * These are the **display vocabulary** for the values Doc 03 §7.1 defines — labels and a filter
 * list, not an API type. A value missing here renders verbatim rather than being dropped, so a
 * status Meta adds later degrades gracefully.
 */
export const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pending: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
  paused: "Paused",
  disabled: "Disabled",
};

export const STATUSES: string[] = Object.keys(STATUS_LABELS);

/** What each approval status means for the operator, shown beside the badge on the detail page. */
export const STATUS_EXPLANATIONS: Record<string, string> = {
  draft: "Saved locally. Meta has not seen it — submit it for review before it can be sent.",
  pending: "Submitted to Meta and awaiting review. Nothing can be sent until it is approved.",
  approved: "Approved by Meta. This template can be broadcast.",
  rejected: "Meta rejected this template. Fix the definition and resubmit.",
  paused: "Meta paused this template, usually for poor quality. Sends are blocked until it recovers.",
  disabled: "Meta disabled this template. It cannot be sent and cannot be recovered by editing.",
};

// --- Lifecycle rules, mirrored from the server so the UI offers only what will be accepted ------
//
// The server remains the authority (Doc 04 §15 answers 409 on a bad transition, and that error is
// surfaced verbatim). These predicates gate presentation, never correctness.

/** `TPL_EDITABLE` — states the platform still owns; anything else is Meta's, and sync would win. */
export function isEditable(template: Template): boolean {
  return template.status === "draft" || template.status === "rejected";
}

/** `TPL_SENDABLE` — only an approved template may be broadcast (FR-TPL-03). */
export function isSendable(template: Template): boolean {
  return template.is_sendable;
}

/** A submit is only meaningful from a state the platform owns and Meta has not accepted. */
export function isSubmittable(template: Template): boolean {
  return isEditable(template);
}

// --- List query (client-side; see `api.ts` for why) ---------------------------------------------

export type TemplateSort = "-created_at" | "created_at" | "name" | "-name" | "-updated_at";

export interface TemplateListQuery {
  q: string;
  status: string;
  category: string;
  language: string;
  sort: TemplateSort;
  page: number;
}

export const DEFAULT_LIST_QUERY: TemplateListQuery = {
  q: "",
  status: "",
  category: "",
  language: "",
  sort: "-created_at",
  page: 1,
};
