import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type SimOrder = components["schemas"]["SimOrderResponse"];
export type SimOrderEvent = components["schemas"]["SimOrderEventResponse"];
export type ActivationRecord = components["schemas"]["ActivationRecordResponse"];
export type SimOrderTransition = components["schemas"]["SimOrderTransitionRequest"];
export type ActivationTransition = components["schemas"]["ActivationTransitionRequest"];

export type SimStatus = SimOrderTransition["to_status"];
export type ActivationStatus = ActivationTransition["to_status"];

/**
 * The lifecycle in order, which is what a queue is *for*: an operator reads down the board and the
 * work moves left to right. Derived from the transition request's own enum, so a status the
 * backend adds cannot silently go missing from the screen.
 */
export const SIM_STATUSES: SimStatus[] = [
  "requested",
  "approved",
  "assigned",
  "dispatched",
  "delivered",
  "failed",
  "cancelled",
];

export const SIM_STATUS_LABELS: Record<SimStatus, string> = {
  requested: "Requested",
  approved: "Approved",
  assigned: "Assigned",
  dispatched: "Dispatched",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const ACTIVATION_STATUSES: ActivationStatus[] = [
  "pending",
  "verification",
  "ready",
  "approved",
  "completed",
  "rejected",
];

export const ACTIVATION_STATUS_LABELS: Record<ActivationStatus, string> = {
  pending: "Pending",
  verification: "In verification",
  ready: "Ready",
  approved: "Approved",
  completed: "Completed",
  rejected: "Rejected",
};

export type Tone = "neutral" | "info" | "success" | "danger" | "warning";

/** Colour carries meaning here, so it is decided once rather than at each call site. */
export const SIM_TONES: Record<SimStatus, Tone> = {
  requested: "neutral",
  approved: "info",
  assigned: "info",
  dispatched: "info",
  delivered: "success",
  failed: "danger",
  cancelled: "warning",
};

export const ACTIVATION_TONES: Record<ActivationStatus, Tone> = {
  pending: "neutral",
  verification: "info",
  ready: "info",
  approved: "info",
  completed: "success",
  rejected: "danger",
};

/** States nothing will move out of on its own; a queue should stop asking about them. */
export const SIM_SETTLED: SimStatus[] = ["delivered", "failed", "cancelled"];
export const ACTIVATION_SETTLED: ActivationStatus[] = ["completed", "rejected"];
