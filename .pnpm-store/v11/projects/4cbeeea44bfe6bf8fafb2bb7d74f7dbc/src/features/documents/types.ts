import type { components, operations } from "@/lib/api/schema";

export type CustomerDocument = components["schemas"]["DocumentResponse"];
export type DocumentVersion = components["schemas"]["DocumentVersionResponse"];
export type DocumentEvent = components["schemas"]["DocumentEventResponse"];
export type DocumentCreateRequest = components["schemas"]["DocumentCreateRequest"];
export type DocumentVersionCreateRequest = components["schemas"]["DocumentVersionCreateRequest"];
export type DocumentVerificationRequest = components["schemas"]["DocumentVerificationRequest"];

type ListQuery = NonNullable<
  operations["list_contact_documents_api_v1_contacts__contact_id__documents_get"]["parameters"]["query"]
>;

export type DocumentStatus = NonNullable<NonNullable<ListQuery["status"]>[number]>;
export type DocumentType = NonNullable<NonNullable<ListQuery["type"]>[number]>;

export interface DocumentFilters {
  q: string;
  status: DocumentStatus | "";
  type: DocumentType | "";
}

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  identity: "Identity proof",
  address: "Address proof",
  income: "Income proof",
  business: "Business document",
  consent: "Consent record",
  other: "Other",
};

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  submitted: "Awaiting review",
  verified: "Verified",
  rejected: "Needs attention",
  expired: "Expired",
  archived: "Archived",
};

export const DOCUMENT_TYPES = Object.keys(DOCUMENT_TYPE_LABELS) as DocumentType[];
export const DOCUMENT_STATUSES = Object.keys(DOCUMENT_STATUS_LABELS) as DocumentStatus[];
