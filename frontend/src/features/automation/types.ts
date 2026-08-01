import type { components } from "@/lib/api/schema";

export type AutomationFlow = components["schemas"]["AutomationFlowResponse"];
export type AutomationGraph = components["schemas"]["AutomationGraph"];
export type AutomationNode = NonNullable<AutomationGraph["nodes"]>[number];
export type AutomationEdge = components["schemas"]["AutomationEdge"];
export type AutomationCreateRequest = components["schemas"]["AutomationCreateRequest"];
export type AutomationUpdateRequest = components["schemas"]["AutomationUpdateRequest"];
export type AutomationValidation = components["schemas"]["AutomationValidationResponse"];
export type AutomationVersion = components["schemas"]["AutomationVersionResponse"];
export type AutomationRun = components["schemas"]["AutomationRunResponse"];
export type AutomationAttempt = components["schemas"]["AutomationAttemptResponse"];
export type AutomationTriggerReceipt = components["schemas"]["AutomationTriggerReceiptResponse"];
export type AutomationStatus = AutomationFlow["status"];

export function graphNodes(graph: AutomationGraph): AutomationNode[] {
  return graph.nodes ?? [];
}

export function graphEdges(graph: AutomationGraph): AutomationEdge[] {
  return graph.edges ?? [];
}
