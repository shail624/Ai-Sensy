import type { AnalyticsKpis, KpiKind } from "@/features/analytics/types";
import { delta, formatKpi, formatRate } from "@/features/analytics/format";
import type { Campaign } from "@/features/campaigns/types";
import type { Conversation } from "@/features/inbox/types";
import type { KycOperationsCard } from "@/features/kyc/types";
import type { ReactivationCard } from "@/features/reactivation/types";
import { REACTIVATION_STAGE_LABELS } from "@/features/reactivation/types";
import type { Template } from "@/features/templates/types";

export type AttentionSeverity = "critical" | "high" | "medium";
export type AttentionSource =
  | "Customer"
  | "KYC"
  | "SIM"
  | "Activation"
  | "Campaign"
  | "Conversation"
  | "Template";

export interface AttentionItem {
  id: string;
  source: AttentionSource;
  title: string;
  detail: string;
  owner: string;
  href: string;
  actionLabel: string;
  severity: AttentionSeverity;
  rank: number;
}

export interface AgentAttentionRow {
  name: string;
  overdue: number;
  slaBreaches: number;
  kycReviews: number;
  blockedCustomers: number;
  total: number;
}

export interface KpiChangeRow {
  key: keyof AnalyticsKpis;
  label: string;
  current: string;
  previous: string;
  change: string;
  sentiment: "positive" | "negative" | "neutral" | "unknown";
  changed: boolean;
}

const BLOCKING_LABELS = new Set(["documents_incomplete", "customer_not_reachable"]);
const TEMPLATE_ACTION_STATUSES = new Set(["rejected", "paused", "disabled"]);

function severityRank(severity: AttentionSeverity): number {
  if (severity === "critical") return 3;
  if (severity === "high") return 2;
  return 1;
}

export function reactivationReasons(card: ReactivationCard): string[] {
  const reasons: string[] = [];
  if (card.sla_status === "breached") reasons.push("SLA breached");
  if (card.reminder_view === "overdue") reasons.push("Follow-up overdue");
  if (card.labels.includes("documents_incomplete")) reasons.push("Documents incomplete");
  if (card.labels.includes("customer_not_reachable")) reasons.push("Customer not reachable");
  return reasons;
}

export function blockedReactivationCards(cards: ReactivationCard[]): ReactivationCard[] {
  return cards
    .filter((card) =>
      card.sla_status === "breached" ||
      card.reminder_view === "overdue" ||
      card.labels.some((label) => BLOCKING_LABELS.has(label)),
    )
    .sort((left, right) => {
      const score = (card: ReactivationCard) =>
        Number(card.sla_status === "breached") * 8 +
        Number(card.reminder_view === "overdue") * 4 +
        Number(card.labels.includes("documents_incomplete")) * 2 +
        Number(card.labels.includes("customer_not_reachable"));
      return score(right) - score(left) || left.contact_name.localeCompare(right.contact_name);
    });
}

export function pendingKycReviews(rows: KycOperationsCard[]): KycOperationsCard[] {
  return rows
    .filter((row) => row.status === "under_review")
    .sort((left, right) =>
      Number(right.sla_status === "breached") - Number(left.sla_status === "breached") ||
      left.contact_name.localeCompare(right.contact_name),
    );
}

export function delayedSimCards(cards: ReactivationCard[]): ReactivationCard[] {
  return cards.filter((card) => card.stage === "sim_required" && card.sla_status === "breached");
}

export function overdueActivationCards(cards: ReactivationCard[]): ReactivationCard[] {
  return cards.filter(
    (card) => card.stage === "activation_pending" && card.sla_status === "breached",
  );
}

export function campaignsNeedingAction(campaigns: Campaign[]): Campaign[] {
  return campaigns
    .filter(
      (campaign) =>
        campaign.status === "failed" ||
        campaign.status === "paused" ||
        campaign.failed_count > 0,
    )
    .sort((left, right) => {
      const score = (campaign: Campaign) =>
        Number(campaign.status === "failed") * 8 +
        Number(campaign.failed_count > 0) * 4 +
        Number(campaign.status === "paused") * 2;
      return score(right) - score(left) || right.failed_count - left.failed_count;
    });
}

export function conversationsNeedingReply(
  conversations: Conversation[],
  now = Date.now(),
): Conversation[] {
  return conversations
    .filter(
      (conversation) =>
        conversation.unread_count > 0 &&
        (conversation.status === "open" || conversation.status === "pending"),
    )
    .sort((left, right) => {
      const leftAt = left.last_message_at ? new Date(left.last_message_at).getTime() : now;
      const rightAt = right.last_message_at ? new Date(right.last_message_at).getTime() : now;
      return leftAt - rightAt;
    });
}

export function templatesNeedingAction(templates: Template[]): Template[] {
  return templates
    .filter((template) => TEMPLATE_ACTION_STATUSES.has(template.status))
    .sort((left, right) => {
      const score = (template: Template) =>
        Number(template.status === "disabled") * 8 +
        Number(template.status === "rejected") * 4 +
        Number(template.status === "paused") * 2;
      return score(right) - score(left) || left.name.localeCompare(right.name);
    });
}

function conversationName(conversation: Conversation): string {
  return conversation.contact?.name ?? conversation.contact?.phone ?? "Unknown contact";
}

export function unreadWaitLabel(conversation: Conversation, now = Date.now()): string {
  if (!conversation.last_message_at) return "Unread reply waiting";
  const minutes = Math.max(
    0,
    Math.round((now - new Date(conversation.last_message_at).getTime()) / 60_000),
  );
  if (minutes < 1) return "Waiting now";
  if (minutes < 60) return `Waiting ${minutes}m`;
  return `Waiting ${Math.round(minutes / 60)}h`;
}

function conversationSeverity(
  conversation: Conversation,
  now: number,
): AttentionSeverity {
  if (!conversation.last_message_at) return "medium";
  const minutes = Math.max(
    0,
    Math.round((now - new Date(conversation.last_message_at).getTime()) / 60_000),
  );
  if (minutes >= 60) return "critical";
  if (minutes >= 15) return "high";
  return "medium";
}

export function buildAttentionQueue({
  reactivation,
  kyc,
  campaigns,
  conversations,
  templates,
  now = Date.now(),
}: {
  reactivation: ReactivationCard[];
  kyc: KycOperationsCard[];
  campaigns: Campaign[];
  conversations: Conversation[];
  templates: Template[];
  now?: number;
}): AttentionItem[] {
  const items: AttentionItem[] = [];

  for (const card of blockedReactivationCards(reactivation)) {
    const reasons = reactivationReasons(card);
    const sim = card.stage === "sim_required" && card.sla_status === "breached";
    const activation = card.stage === "activation_pending" && card.sla_status === "breached";
    const source: AttentionSource = sim ? "SIM" : activation ? "Activation" : "Customer";
    const title = sim
      ? `${card.contact_name} has delayed SIM work`
      : activation
        ? `${card.contact_name} has an overdue activation`
        : `${card.contact_name} is blocked`;
    const severity: AttentionSeverity = card.sla_status === "breached" ? "critical" : "high";
    items.push({
      id: `reactivation:${card.id}`,
      source,
      title,
      detail: `${REACTIVATION_STAGE_LABELS[card.stage]} · ${reasons.join(" · ")}`,
      owner: card.owner_name ?? "Unassigned",
      href: "/reactivation/pipeline",
      actionLabel: "Open case queue",
      severity,
      rank: severityRank(severity) * 100 + reasons.length,
    });
  }

  for (const row of kyc) {
    const needsReview = row.status === "under_review";
    const breached = row.sla_status === "breached";
    const missing = !row.checklist_complete;
    if (!needsReview && !breached && !missing) continue;
    const severity: AttentionSeverity = breached ? "critical" : needsReview ? "high" : "medium";
    const details = [
      needsReview ? "Reviewer action pending" : null,
      breached ? "SLA breached" : null,
      missing ? "Evidence incomplete" : null,
    ].filter((item): item is string => Boolean(item));
    items.push({
      id: `kyc:${row.id}`,
      source: "KYC",
      title: `${row.contact_name} needs KYC attention`,
      detail: details.join(" · "),
      owner: row.owner_name ?? "Unassigned",
      href: "/reactivation/kyc",
      actionLabel: "Open KYC queue",
      severity,
      rank: severityRank(severity) * 100 + details.length,
    });
  }

  for (const campaign of campaignsNeedingAction(campaigns)) {
    const severity: AttentionSeverity = campaign.status === "failed" ? "critical" : "high";
    const detail = campaign.failed_count > 0
      ? `${campaign.failed_count.toLocaleString()} failed recipients`
      : campaign.status === "paused"
        ? "Paused and awaiting an operator decision"
        : "Campaign execution failed";
    items.push({
      id: `campaign:${campaign.id}`,
      source: "Campaign",
      title: campaign.name,
      detail,
      owner: "Campaign operations",
      href: `/campaigns/${campaign.id}`,
      actionLabel: "Review campaign",
      severity,
      rank: severityRank(severity) * 100 + campaign.failed_count,
    });
  }

  for (const conversation of conversationsNeedingReply(conversations, now)) {
    const severity = conversationSeverity(conversation, now);
    items.push({
      id: `conversation:${conversation.id}`,
      source: "Conversation",
      title: `${conversationName(conversation)} is waiting for a reply`,
      detail: `${conversation.unread_count} unread · ${unreadWaitLabel(conversation, now)}`,
      owner: "Inbox queue",
      href: "/inbox",
      actionLabel: "Open inbox",
      severity,
      rank: severityRank(severity) * 100 + conversation.unread_count,
    });
  }

  for (const template of templatesNeedingAction(templates)) {
    const severity: AttentionSeverity = template.status === "disabled" ? "critical" : "high";
    items.push({
      id: `template:${template.id}`,
      source: "Template",
      title: template.name,
      detail:
        template.status === "rejected" && template.rejection_reason
          ? `Rejected · ${template.rejection_reason}`
          : `${template.status[0]?.toUpperCase()}${template.status.slice(1)} by Meta`,
      owner: "Template operations",
      href: `/templates/${template.id}`,
      actionLabel: "Review template",
      severity,
      rank: severityRank(severity) * 100,
    });
  }

  return items.sort(
    (left, right) =>
      right.rank - left.rank || left.source.localeCompare(right.source) || left.title.localeCompare(right.title),
  );
}

export function agentAttention(
  reactivation: ReactivationCard[],
  kyc: KycOperationsCard[],
): AgentAttentionRow[] {
  const rows = new Map<string, AgentAttentionRow>();
  const ensure = (name: string): AgentAttentionRow => {
    const existing = rows.get(name);
    if (existing) return existing;
    const created: AgentAttentionRow = {
      name,
      overdue: 0,
      slaBreaches: 0,
      kycReviews: 0,
      blockedCustomers: 0,
      total: 0,
    };
    rows.set(name, created);
    return created;
  };

  for (const card of blockedReactivationCards(reactivation)) {
    const row = ensure(card.owner_name ?? "Unassigned");
    row.blockedCustomers += 1;
    if (card.reminder_view === "overdue") row.overdue += 1;
    if (card.sla_status === "breached") row.slaBreaches += 1;
  }

  for (const item of kyc) {
    if (item.status !== "under_review" && item.sla_status !== "breached") continue;
    const row = ensure(item.owner_name ?? "Unassigned");
    if (item.status === "under_review") row.kycReviews += 1;
    if (item.sla_status === "breached") row.slaBreaches += 1;
  }

  for (const row of rows.values()) {
    row.total = row.overdue + row.slaBreaches + row.kycReviews + row.blockedCustomers;
  }

  return [...rows.values()].sort(
    (left, right) =>
      Number(right.name === "Unassigned") - Number(left.name === "Unassigned") ||
      right.total - left.total ||
      left.name.localeCompare(right.name),
  );
}

const KPI_SPECS: Array<{
  key: keyof AnalyticsKpis;
  label: string;
  kind: KpiKind;
  lowerIsBetter?: boolean;
}> = [
  { key: "delivery_rate", label: "Delivery rate", kind: "rate" },
  { key: "read_rate", label: "Read rate", kind: "rate" },
  { key: "failure_rate", label: "Failure rate", kind: "rate", lowerIsBetter: true },
  {
    key: "avg_first_response_seconds",
    label: "First response",
    kind: "duration",
    lowerIsBetter: true,
  },
  { key: "task_completion_rate", label: "Task completion", kind: "rate" },
  { key: "task_on_time_rate", label: "Tasks on time", kind: "rate" },
];

export function kpiChanges(
  current: AnalyticsKpis | null | undefined,
  previous: AnalyticsKpis | null | undefined,
): KpiChangeRow[] {
  return KPI_SPECS.map((spec): KpiChangeRow => {
    const currentValue = current?.[spec.key];
    const previousValue = previous?.[spec.key];
    const change = delta(currentValue, previousValue);
    const changed = change !== null && change !== 0;
    const positive = change !== null && ((change > 0) !== Boolean(spec.lowerIsBetter));
    const sentiment: KpiChangeRow["sentiment"] =
      change === null
        ? "unknown"
        : change === 0
          ? "neutral"
          : positive
            ? "positive"
            : "negative";
    return {
      key: spec.key,
      label: spec.label,
      current: formatKpi(currentValue, spec.kind),
      previous: formatKpi(previousValue, spec.kind),
      change:
        change === null
          ? "No comparison"
          : change === 0
            ? "No change"
            : `${change > 0 ? "+" : ""}${formatRate(change)}`,
      sentiment,
      changed,
    };
  }).sort(
    (left, right) => Number(right.changed) - Number(left.changed) || left.label.localeCompare(right.label),
  );
}
