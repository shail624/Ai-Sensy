import type { components, operations } from "@/lib/api/schema";

export type KycCase = components["schemas"]["KycCaseResponse"];
export type KycOperationsCard = components["schemas"]["KycOperationsCardResponse"];
export type KycOperationsResponse = components["schemas"]["KycOperationsResponse"];
export type KycDecision = components["schemas"]["KycDecisionResponse"];
export type KycDocumentReference = components["schemas"]["KycDocumentReferenceResponse"];
export type KycAppointment = components["schemas"]["KycAppointmentResponse"];
export type KycStatus = KycCase["status"];
export type KycReasonCode = NonNullable<KycDecision["reason_code"]>;
export type KycDocumentPurpose = KycDocumentReference["purpose"];

type OperationsQuery = NonNullable<
  operations["get_kyc_operations_api_v1_kyc_operations_get"]["parameters"]["query"]
>;

export interface KycFilters {
  q?: OperationsQuery["q"];
  kyc_status?: OperationsQuery["kyc_status"];
  limit?: OperationsQuery["limit"];
}

export const KYC_STATUS_LABELS: Record<KycStatus, string> = {
  pending: "Pending",
  documents_pending: "Documents pending",
  under_review: "Under review",
  approved: "Approved",
  rejected: "Rejected",
};

export const KYC_REASON_LABELS: Record<KycReasonCode, string> = {
  holder_mismatch: "Original holder mismatch",
  delhi_presence_unverified: "Delhi presence not verified",
  active_number_unverified: "Active number not verified",
  aadhaar_missing: "Aadhaar reference missing",
  pan_missing: "PAN reference missing",
  document_unreadable: "Document unreadable",
  document_mismatch: "Document details mismatch",
  customer_unavailable: "Customer unavailable",
  other: "Other governed reason",
};

export const KYC_DOCUMENT_LABELS: Record<KycDocumentPurpose, string> = {
  aadhaar: "Aadhaar proof",
  pan: "PAN proof",
};
