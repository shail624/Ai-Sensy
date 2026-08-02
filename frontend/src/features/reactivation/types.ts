import type { components, operations } from "@/lib/api/schema";

export type ReactivationCard = components["schemas"]["ReactivationPipelineCardResponse"];
export type ReactivationPipeline = components["schemas"]["ReactivationPipelineResponse"];
export type ReactivationStage = ReactivationCard["stage"];
export type ReactivationStageEvent = components["schemas"]["ReactivationStageEventResponse"];
export type ReactivationNote = components["schemas"]["ReactivationNoteResponse"];
export type EligibilityCheck = components["schemas"]["EligibilityCheckResponse"];

type PipelineQuery = NonNullable<
  operations["get_reactivation_pipeline_api_v1_reactivation_pipeline_get"]["parameters"]["query"]
>;

export interface ReactivationFilters {
  q?: PipelineQuery["q"];
  stage?: PipelineQuery["stage"];
  owner_user_id?: PipelineQuery["owner_user_id"];
  limit?: PipelineQuery["limit"];
}

export const REACTIVATION_STAGES: readonly ReactivationStage[] = [
  "new_lead",
  "follow_up",
  "interested",
  "eligibility_check",
  "eligible",
  "documents_pending",
  "documents_received",
  "kyc_pending",
  "verification",
  "confirmed",
  "sim_order",
  "activation_pending",
  "completed",
  "not_eligible",
  "not_interested",
] as const;

export const REACTIVATION_STAGE_LABELS: Record<ReactivationStage, string> = {
  new_lead: "New lead",
  follow_up: "Follow-up",
  interested: "Interested",
  eligibility_check: "Eligibility check",
  eligible: "Eligible",
  documents_pending: "Documents pending",
  documents_received: "Documents received",
  kyc_pending: "KYC pending",
  verification: "Verification",
  confirmed: "Confirmed",
  sim_order: "SIM order",
  activation_pending: "Activation pending",
  completed: "Completed",
  not_eligible: "Not eligible",
  not_interested: "Not interested",
};

export function stageIndex(stage: ReactivationStage): number {
  return REACTIVATION_STAGES.indexOf(stage);
}
