import { describe, expect, it } from "vitest";

import {
  agentAttention,
  blockedReactivationCards,
  buildAttentionQueue,
  campaignsNeedingAction,
  conversationsNeedingReply,
  delayedSimCards,
  kpiChanges,
  overdueActivationCards,
  pendingKycReviews,
  templatesNeedingAction,
} from "@/features/dashboard/selectors";
import type { Campaign } from "@/features/campaigns/types";
import type { Conversation } from "@/features/inbox/types";
import type { KycOperationsCard } from "@/features/kyc/types";
import type { ReactivationCard } from "@/features/reactivation/types";
import type { Template } from "@/features/templates/types";

const baseCard = {
  id: "case-1",
  contact_name: "Asha Mehta",
  contact_phone: "+919999999999",
  stage: "documents_pending",
  labels: [],
  reminder_view: null,
  owner_name: "Priya Shah",
  owner_user_id: "user-1",
  sla_status: "on_track",
  document_count: 0,
  verified_document_count: 0,
  available_transitions: [],
} as unknown as ReactivationCard;

const baseKyc = {
  id: "kyc-1",
  contact_name: "Nisha Rao",
  contact_phone: "+918888888888",
  owner_name: "Priya Shah",
  status: "pending",
  progress_percent: 40,
  checklist: [],
  checklist_complete: false,
  appointments: [],
  sla_status: "on_track",
} as unknown as KycOperationsCard;

const baseCampaign = {
  id: "campaign-1",
  name: "Reactivation reminder",
  status: "completed",
  failed_count: 0,
} as unknown as Campaign;

const baseConversation = {
  id: "conversation-1",
  contact: { id: "contact-1", name: "Ravi Kumar", phone: "+917777777777" },
  status: "open",
  unread_count: 0,
  last_message_at: "2026-08-04T00:00:00Z",
} as unknown as Conversation;

const baseTemplate = {
  id: "template-1",
  name: "reactivation_notice",
  status: "approved",
  rejection_reason: null,
} as unknown as Template;

describe("operational dashboard selectors", () => {
  it("separates real blockers, SIM risk and activation SLA breaches without treating priority alone as blocked", () => {
    const cards = [
      { ...baseCard, id: "priority", labels: ["priority"] },
      { ...baseCard, id: "blocked", labels: ["documents_incomplete"] },
      { ...baseCard, id: "sim", stage: "sim_required", sla_status: "breached" },
      { ...baseCard, id: "activation", stage: "activation_pending", sla_status: "breached" },
    ] as ReactivationCard[];

    expect(blockedReactivationCards(cards).map((card) => card.id)).not.toContain("priority");
    expect(blockedReactivationCards(cards).map((card) => card.id)).toEqual(
      expect.arrayContaining(["blocked", "sim", "activation"]),
    );
    expect(delayedSimCards(cards).map((card) => card.id)).toEqual(["sim"]);
    expect(overdueActivationCards(cards).map((card) => card.id)).toEqual(["activation"]);
  });

  it("finds actionable KYC, campaign, conversation and template records from persisted statuses", () => {
    const kyc = [baseKyc, { ...baseKyc, id: "review", status: "under_review" }] as KycOperationsCard[];
    const campaigns = [baseCampaign, { ...baseCampaign, id: "failed", status: "failed", failed_count: 14 }] as Campaign[];
    const conversations = [baseConversation, { ...baseConversation, id: "waiting", unread_count: 3, last_message_at: "2026-08-03T22:00:00Z" }] as Conversation[];
    const templates = [baseTemplate, { ...baseTemplate, id: "rejected", status: "rejected", rejection_reason: "Policy" }] as Template[];

    expect(pendingKycReviews(kyc).map((row) => row.id)).toEqual(["review"]);
    expect(campaignsNeedingAction(campaigns).map((row) => row.id)).toEqual(["failed"]);
    expect(conversationsNeedingReply(conversations, new Date("2026-08-04T02:00:00Z").getTime()).map((row) => row.id)).toEqual(["waiting"]);
    expect(templatesNeedingAction(templates).map((row) => row.id)).toEqual(["rejected"]);
  });

  it("prioritizes critical cross-domain work and exposes agent load without inventing performance scores", () => {
    const cards = [
      { ...baseCard, id: "overdue", reminder_view: "overdue" },
      { ...baseCard, id: "unassigned", owner_name: null, sla_status: "breached" },
    ] as ReactivationCard[];
    const kyc = [{ ...baseKyc, status: "under_review", sla_status: "breached" }] as KycOperationsCard[];
    const campaigns = [{ ...baseCampaign, status: "failed", failed_count: 2 }] as Campaign[];
    const conversations = [{ ...baseConversation, unread_count: 1, last_message_at: "2026-08-03T22:00:00Z" }] as Conversation[];
    const templates = [{ ...baseTemplate, status: "disabled" }] as Template[];

    const queue = buildAttentionQueue({
      reactivation: cards,
      kyc,
      campaigns,
      conversations,
      templates,
      now: new Date("2026-08-04T02:00:00Z").getTime(),
    });
    expect(queue[0]?.severity).toBe("critical");
    expect(queue.map((item) => item.source)).toEqual(
      expect.arrayContaining(["Customer", "KYC", "Campaign", "Conversation", "Template"]),
    );

    const agents = agentAttention(cards, kyc);
    expect(agents[0]?.name).toBe("Unassigned");
    expect(agents.find((row) => row.name === "Priya Shah")).toMatchObject({
      overdue: 1,
      kycReviews: 1,
    });
  });

  it("interprets today KPI direction according to the metric instead of treating every increase as good", () => {
    const rows = kpiChanges(
      {
        delivery_rate: 0.9,
        read_rate: 0.7,
        failure_rate: 0.08,
        avg_first_response_seconds: 120,
        task_completion_rate: 0.8,
        task_on_time_rate: 0.75,
      } as never,
      {
        delivery_rate: 0.8,
        read_rate: 0.7,
        failure_rate: 0.04,
        avg_first_response_seconds: 60,
        task_completion_rate: 0.7,
        task_on_time_rate: 0.75,
      } as never,
    );

    expect(rows.find((row) => row.key === "delivery_rate")?.sentiment).toBe("positive");
    expect(rows.find((row) => row.key === "failure_rate")?.sentiment).toBe("negative");
    expect(rows.find((row) => row.key === "avg_first_response_seconds")?.sentiment).toBe("negative");
    expect(rows.find((row) => row.key === "read_rate")?.change).toBe("No change");
  });
});
