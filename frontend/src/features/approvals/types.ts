import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type KycCase = components["schemas"]["KycCaseResponse"];
export type ActivationRecord = components["schemas"]["ActivationRecordResponse"];

/**
 * One thing waiting on somebody's approval, whatever module it came from.
 *
 * Deliberately a *view* over records that already exist rather than a row in an approvals table.
 * `MODULE_STATUS` records that CORE-08 was skipped as "not required by product owner", and what it
 * refused was a generic approval **authority** — a second place where permission to act is
 * decided. Nothing here decides anything: each item is approved through the endpoint its own
 * module already owns, under the permission that module already checks.
 */
export interface PendingApproval {
  id: string;
  source: "kyc" | "activation";
  /** What the operator is being asked to approve, in that module's own words. */
  label: string;
  detail: string;
  contactId: string | null;
  rowVersion: number;
  waitingSince: string;
}

export const SOURCE_LABELS: Record<PendingApproval["source"], string> = {
  kyc: "KYC",
  activation: "Activation",
};

/** The one state in each lifecycle that means "a person must now decide". */
export const KYC_AWAITING = "under_review";
export const ACTIVATION_AWAITING = "ready";

/** The permission each source's approval already requires; nothing new is introduced. */
export const SOURCE_PERMISSION: Record<PendingApproval["source"], string> = {
  kyc: "kyc:approve",
  activation: "activation:approve",
};

export function kycToApproval(row: KycCase): PendingApproval {
  return {
    id: row.id,
    source: "kyc",
    label: "KYC verification",
    detail: [
      row.holder_verified ? "holder verified" : "holder unverified",
      row.delhi_presence_verified ? "Delhi presence verified" : "Delhi presence unverified",
    ].join(" · "),
    contactId: row.contact_id ?? null,
    rowVersion: row.row_version,
    waitingSince: row.created_at,
  };
}

export function activationToApproval(row: ActivationRecord): PendingApproval {
  return {
    id: row.id,
    source: "activation",
    label: row.approval_reference ?? "Activation record",
    detail: "Ready for activation approval",
    contactId: row.contact_id ?? null,
    rowVersion: row.row_version,
    waitingSince: row.created_at,
  };
}

/** Oldest first: the thing that has been waiting longest is the thing most worth deciding. */
export function byWaitingLongest(a: PendingApproval, b: PendingApproval): number {
  return a.waitingSince < b.waitingSince ? -1 : a.waitingSince > b.waitingSince ? 1 : 0;
}
