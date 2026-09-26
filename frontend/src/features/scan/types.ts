import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type ReachabilityRow = components["schemas"]["ReachabilityResponse"];
export type ReachabilityPage = components["schemas"]["ReachabilityPage"];
export type ReachabilityCounts = components["schemas"]["ReachabilityCounts"];
export type Verdict = ReachabilityRow["verdict"];

/** What each verdict means, in the words an operator would use for it. */
export const VERDICT_LABELS: Record<Verdict, string> = {
  reachable: "On WhatsApp",
  unreachable: "Not on WhatsApp",
  unknown: "Never messaged",
};

/**
 * The sentence under each tally.
 *
 * "Never messaged" is the one worth spelling out: it is not a softer "no", it means the number has
 * never been tested, and the next action for those contacts is a campaign rather than a cleanup.
 */
export const VERDICT_HINTS: Record<Verdict, string> = {
  reachable: "WhatsApp confirmed delivery to these numbers.",
  unreachable: "WhatsApp refused these numbers as not registered.",
  unknown: "No campaign has ever included these numbers, so nothing is known either way.",
};
