import type { KycOperationsCard } from "@/features/kyc/types";
import type { ReactivationCard, ReactivationStage } from "@/features/reactivation/types";

export type ReactivationOperationalView =
  | "all"
  | "attention"
  | "overdue"
  | "due_today"
  | "documents"
  | "kyc"
  | "sim"
  | "activation"
  | "release"
  | "unassigned"
  | "priority";

export type AttentionSeverity = "critical" | "high" | "medium" | "normal";

export interface OperationalViewDefinition {
  value: ReactivationOperationalView;
  label: string;
  description: string;
}

export interface ReactivationAttentionSignal {
  card: ReactivationCard;
  score: number;
  severity: AttentionSeverity;
  reasons: string[];
  nextAction: string;
}

export interface ReactivationMissionSnapshot {
  active: number;
  attention: number;
  overdue: number;
  blocked: number;
  pendingKyc: number;
  missingKycEvidence: number;
  documentGaps: number;
  simRisk: number;
  activationRisk: number;
  releaseRisk: number;
  unassigned: number;
  completed: number;
  topAttention: ReactivationAttentionSignal[];
}

export const REACTIVATION_OPERATIONAL_VIEWS: readonly OperationalViewDefinition[] = [
  { value: "attention", label: "Attention now", description: "Highest urgency across SLA, reminders, release dates, evidence and ownership." },
  { value: "overdue", label: "Overdue", description: "Cases with an overdue reminder, overdue task or breached SLA." },
  { value: "due_today", label: "Due today", description: "Assigned reminders that require action today." },
  { value: "documents", label: "Document gaps", description: "Cases waiting for documents or carrying incomplete evidence." },
  { value: "kyc", label: "KYC", description: "Cases at the governed KYC or verification stage." },
  { value: "sim", label: "SIM risk", description: "SIM-required cases with time, ownership or SLA risk." },
  { value: "activation", label: "Activation risk", description: "Activation-pending cases needing a final hand-off." },
  { value: "release", label: "Release risk", description: "Name-change cases whose release date is overdue or within three days." },
  { value: "unassigned", label: "Unassigned", description: "Active cases without an accountable owner." },
  { value: "priority", label: "Priority", description: "Cases explicitly marked Priority by an operator." },
  { value: "all", label: "All cases", description: "Every case in the currently loaded tenant-scoped operating set." },
] as const;

const TERMINAL_STAGES = new Set<ReactivationStage>(["completed", "not_required"]);
const DAY_MS = 86_400_000;

export function isActiveReactivation(card: ReactivationCard): boolean {
  return !TERMINAL_STAGES.has(card.stage);
}

export function releaseRiskLabel(card: ReactivationCard, now = new Date()): string | null {
  if (!card.release_at || !card.labels.includes("name_change") || !isActiveReactivation(card)) return null;
  const delta = new Date(card.release_at).getTime() - now.getTime();
  if (delta < 0) return "Release date overdue";
  if (delta <= DAY_MS) return "Release due within 24 hours";
  if (delta <= DAY_MS * 3) return "Release due within 3 days";
  return null;
}

export function blockerReasons(card: ReactivationCard, now = new Date()): string[] {
  if (!isActiveReactivation(card)) return [];
  const reasons: string[] = [];
  if (card.sla_status === "breached") reasons.push("SLA breached");
  if (card.reminder_view === "overdue" || card.overdue_task_count > 0) reasons.push("Follow-up overdue");
  const releaseRisk = releaseRiskLabel(card, now);
  if (releaseRisk) reasons.push(releaseRisk);
  if (card.labels.includes("customer_not_reachable")) reasons.push("Customer not reachable");
  if (
    card.stage === "documents_pending" ||
    card.labels.includes("documents_incomplete") ||
    card.verified_document_count < card.document_count
  ) reasons.push("Document evidence incomplete");
  if (card.latest_eligibility_status === "review_required") reasons.push("Eligibility review required");
  if (!card.owner_user_id) reasons.push("Owner not assigned");
  return Array.from(new Set(reasons));
}

export function nextRequiredAction(card: ReactivationCard, now = new Date()): string {
  const reasons = blockerReasons(card, now);
  if (reasons.includes("SLA breached")) return "Resolve the breached SLA and record the next action";
  if (reasons.includes("Release date overdue") || reasons.includes("Release due within 24 hours") || reasons.includes("Release due within 3 days")) return "Resolve the release-date dependency";
  if (reasons.includes("Follow-up overdue")) return "Complete or reschedule the overdue follow-up";
  if (reasons.includes("Customer not reachable")) return "Retry customer contact and update the case";
  if (reasons.includes("Document evidence incomplete")) return "Collect and verify the missing documents";
  if (reasons.includes("Eligibility review required")) return "Complete the eligibility review";
  if (reasons.includes("Owner not assigned")) return "Assign an accountable owner";

  switch (card.stage) {
    case "new_lead": return "Confirm customer interest and eligibility";
    case "lead_confirmed": return "Request the required documents";
    case "documents_pending": return "Collect the pending evidence";
    case "documents_received": return "Open the governed KYC review";
    case "kyc_verification": return "Complete KYC review and decision";
    case "sim_required": return "Confirm SIM fulfilment and customer availability";
    case "activation_pending": return "Complete the activation hand-off";
    case "completed": return "No action required";
    case "not_required": return "No action required";
  }
}

export function urgencyScore(card: ReactivationCard, now = new Date()): number {
  if (!isActiveReactivation(card)) return 0;
  let score = 0;
  if (card.sla_status === "breached") score += 120;
  if (card.reminder_view === "overdue") score += 100;
  score += Math.min(card.overdue_task_count, 5) * 12;
  const releaseRisk = releaseRiskLabel(card, now);
  if (releaseRisk === "Release date overdue") score += 110;
  else if (releaseRisk === "Release due within 24 hours") score += 90;
  else if (releaseRisk) score += 70;
  if (card.labels.includes("priority")) score += 60;
  if (card.labels.includes("customer_not_reachable")) score += 55;
  if (card.labels.includes("documents_incomplete")) score += 50;
  if (card.stage === "documents_pending") score += 45;
  if (card.latest_eligibility_status === "review_required") score += 40;
  if (card.reminder_view === "due_today") score += 35;
  if (!card.owner_user_id) score += 30;
  if (card.stage === "kyc_verification") score += 28;
  if (card.stage === "sim_required") score += 34;
  if (card.stage === "activation_pending") score += 38;
  return score;
}

export function attentionSeverity(card: ReactivationCard, now = new Date()): AttentionSeverity {
  const score = urgencyScore(card, now);
  if (score >= 120) return "critical";
  if (score >= 70) return "high";
  if (score >= 30) return "medium";
  return "normal";
}

export function toAttentionSignal(card: ReactivationCard, now = new Date()): ReactivationAttentionSignal {
  return {
    card,
    score: urgencyScore(card, now),
    severity: attentionSeverity(card, now),
    reasons: blockerReasons(card, now),
    nextAction: nextRequiredAction(card, now),
  };
}

export function compareByUrgency(a: ReactivationCard, b: ReactivationCard, now = new Date()): number {
  const scoreDifference = urgencyScore(b, now) - urgencyScore(a, now);
  if (scoreDifference !== 0) return scoreDifference;
  const aDue = a.follow_up_at ? new Date(a.follow_up_at).getTime() : Number.POSITIVE_INFINITY;
  const bDue = b.follow_up_at ? new Date(b.follow_up_at).getTime() : Number.POSITIVE_INFINITY;
  if (aDue !== bDue) return aDue - bDue;
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

export function matchesOperationalView(
  card: ReactivationCard,
  view: ReactivationOperationalView,
  now = new Date(),
): boolean {
  switch (view) {
    case "all": return true;
    case "attention": return urgencyScore(card, now) >= 30;
    case "overdue": return card.reminder_view === "overdue" || card.overdue_task_count > 0 || card.sla_status === "breached";
    case "due_today": return card.reminder_view === "due_today";
    case "documents": return card.stage === "documents_pending" || card.labels.includes("documents_incomplete") || card.verified_document_count < card.document_count;
    case "kyc": return card.stage === "kyc_verification";
    case "sim": return card.stage === "sim_required";
    case "activation": return card.stage === "activation_pending";
    case "release": return releaseRiskLabel(card, now) !== null;
    case "unassigned": return isActiveReactivation(card) && !card.owner_user_id;
    case "priority": return card.labels.includes("priority");
  }
}

export function buildMissionSnapshot(
  cards: ReactivationCard[],
  kycRows: KycOperationsCard[],
  now = new Date(),
): ReactivationMissionSnapshot {
  const activeCards = cards.filter(isActiveReactivation);
  const signals = activeCards
    .map((card) => toAttentionSignal(card, now))
    .filter((signal) => signal.score >= 30)
    .sort((a, b) => b.score - a.score || compareByUrgency(a.card, b.card, now));
  const pendingKycRows = kycRows.filter((row) => ["pending", "documents_pending", "under_review"].includes(row.status));

  return {
    active: activeCards.length,
    attention: signals.length,
    overdue: activeCards.filter((card) => matchesOperationalView(card, "overdue", now)).length,
    blocked: activeCards.filter((card) => blockerReasons(card, now).length > 0).length,
    pendingKyc: pendingKycRows.length || activeCards.filter((card) => card.stage === "kyc_verification").length,
    missingKycEvidence: pendingKycRows.filter((row) => !row.checklist_complete).length,
    documentGaps: activeCards.filter((card) => matchesOperationalView(card, "documents", now)).length,
    simRisk: activeCards.filter((card) => card.stage === "sim_required" && urgencyScore(card, now) >= 30).length,
    activationRisk: activeCards.filter((card) => card.stage === "activation_pending" && urgencyScore(card, now) >= 30).length,
    releaseRisk: activeCards.filter((card) => matchesOperationalView(card, "release", now)).length,
    unassigned: activeCards.filter((card) => !card.owner_user_id).length,
    completed: cards.filter((card) => card.stage === "completed").length,
    topAttention: signals.slice(0, 10),
  };
}
