import type { components, operations } from "@/lib/api/schema";

export type ReactivationCard = components["schemas"]["ReactivationPipelineCardResponse"];
export type ReactivationPipeline = components["schemas"]["ReactivationPipelineResponse"];
export type ReactivationStage = ReactivationCard["stage"];
export type ReactivationStageEvent = components["schemas"]["ReactivationStageEventResponse"];
export type ReactivationHistoryStage = NonNullable<ReactivationStageEvent["from_stage"]>;
export type ReactivationLabel = ReactivationCard["labels"][number];
export type ReactivationNote = components["schemas"]["ReactivationNoteResponse"];
export type EligibilityCheck = components["schemas"]["EligibilityCheckResponse"];

type PipelineQuery = NonNullable<
  operations["get_reactivation_pipeline_api_v1_reactivation_pipeline_get"]["parameters"]["query"]
>;

export interface ReactivationFilters {
  q?: PipelineQuery["q"];
  stage?: PipelineQuery["stage"];
  label?: PipelineQuery["label"];
  owner_user_id?: PipelineQuery["owner_user_id"];
  reminder_view?: PipelineQuery["reminder_view"];
  reminder_date?: PipelineQuery["reminder_date"];
  offset?: PipelineQuery["offset"];
  limit?: PipelineQuery["limit"];
}

export const REACTIVATION_STAGES: readonly ReactivationStage[] = [
  "new_lead",
  "lead_confirmed",
  "documents_pending",
  "documents_received",
  "kyc_verification",
  "sim_required",
  "activation_pending",
  "completed",
  "not_required",
] as const;

export const REACTIVATION_STAGE_LABELS: Record<ReactivationHistoryStage, string> = {
  new_lead: "New Lead",
  lead_confirmed: "Lead Confirmed",
  documents_pending: "Documents Pending",
  documents_received: "Documents Received",
  kyc_verification: "KYC / Verification",
  sim_required: "SIM Required",
  activation_pending: "Activation Pending",
  completed: "Completed",
  not_required: "Not Required",
  follow_up: "Follow-up (legacy)",
  interested: "Interested (legacy)",
  eligibility_check: "Eligibility check (legacy)",
  eligible: "Eligible (legacy)",
  kyc_pending: "KYC pending (legacy)",
  verification: "Verification (legacy)",
  confirmed: "Confirmed (legacy)",
  sim_order: "SIM order (legacy)",
  not_eligible: "Not eligible (legacy)",
  not_interested: "Not interested (legacy)",
};

export const REACTIVATION_LABELS: readonly ReactivationLabel[] = [
  "follow_up",
  "prepaid_required",
  "name_change",
  "priority",
  "customer_not_reachable",
  "documents_incomplete",
] as const;

export const REACTIVATION_LABEL_NAMES: Record<ReactivationLabel, string> = {
  follow_up: "Follow-up",
  prepaid_required: "Prepaid Required",
  name_change: "Name Change",
  priority: "Priority",
  customer_not_reachable: "Customer Not Reachable",
  documents_incomplete: "Documents Incomplete",
};

export function stageIndex(stage: ReactivationStage): number {
  return REACTIVATION_STAGES.indexOf(stage);
}
