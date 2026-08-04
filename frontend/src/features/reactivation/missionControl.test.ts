import { describe, expect, it } from "vitest";

import type { KycOperationsResponse } from "@/features/kyc/types";
import {
  blockerReasons,
  buildMissionSnapshot,
  compareByUrgency,
  matchesOperationalView,
  nextRequiredAction,
  releaseRiskLabel,
  urgencyScore,
} from "@/features/reactivation/missionControl";
import type { ReactivationCard } from "@/features/reactivation/types";

const NOW = new Date("2026-08-04T08:00:00Z");

function makeCard(overrides: Partial<ReactivationCard> = {}): ReactivationCard {
  return {
    id: "case-1",
    contact_id: "contact-1",
    stage: "new_lead",
    available_transitions: ["lead_confirmed"],
    owner_user_id: "user-1",
    previous_vi_number: "9811111111",
    active_delhi_number: "9822222222",
    source: "campaign",
    closed_reason: null,
    row_version: 2,
    created_at: "2026-08-01T08:00:00Z",
    updated_at: "2026-08-03T08:00:00Z",
    contact_name: "Asha Mehra",
    contact_phone: "+919811111111",
    contact_email: "asha@example.test",
    contact_attributes: {},
    owner_name: "Priya Shah",
    stage_entered_at: "2026-08-02T08:00:00Z",
    latest_eligibility_status: "eligible",
    latest_eligibility_reason: null,
    open_task_count: 0,
    overdue_task_count: 0,
    next_task_due_at: null,
    document_count: 0,
    verified_document_count: 0,
    sla_status: "on_track",
    sla_due_at: "2026-08-05T08:00:00Z",
    reservation_status: null,
    family_plan_required: false,
    family_numbers: [],
    conversion_indicator: "open",
    labels: [],
    reminders: [],
    follow_up_at: null,
    release_at: null,
    reminder_view: null,
    ...overrides,
  };
}

describe("Reactivation Mission Control decision model", () => {
  it("prioritizes breached SLA, overdue work and release-date risk", () => {
    const critical = makeCard({
      sla_status: "breached",
      reminder_view: "overdue",
      overdue_task_count: 2,
      labels: ["name_change", "priority"],
      release_at: "2026-08-03T08:00:00Z",
    });
    const normal = makeCard({ id: "case-2", contact_id: "contact-2" });

    expect(urgencyScore(critical, NOW)).toBeGreaterThan(urgencyScore(normal, NOW));
    expect(blockerReasons(critical, NOW)).toEqual(expect.arrayContaining([
      "SLA breached",
      "Follow-up overdue",
      "Release date overdue",
    ]));
    expect(nextRequiredAction(critical, NOW)).toMatch(/breached SLA/i);
    expect([critical, normal].sort((a, b) => compareByUrgency(a, b, NOW))[0]?.id).toBe("case-1");
  });

  it("classifies operational views without inventing a second workflow", () => {
    const documentGap = makeCard({
      stage: "documents_pending",
      document_count: 3,
      verified_document_count: 1,
      labels: ["documents_incomplete"],
    });
    const simRisk = makeCard({ id: "case-2", contact_id: "contact-2", stage: "sim_required", owner_user_id: null, owner_name: null });

    expect(matchesOperationalView(documentGap, "documents", NOW)).toBe(true);
    expect(matchesOperationalView(documentGap, "sim", NOW)).toBe(false);
    expect(matchesOperationalView(simRisk, "sim", NOW)).toBe(true);
    expect(matchesOperationalView(simRisk, "unassigned", NOW)).toBe(true);
  });

  it("surfaces a release window only for active name-change cases", () => {
    const dueSoon = makeCard({ labels: ["name_change"], release_at: "2026-08-06T07:00:00Z" });
    const completed = makeCard({ stage: "completed", labels: ["name_change"], release_at: "2026-08-03T08:00:00Z" });

    expect(releaseRiskLabel(dueSoon, NOW)).toBe("Release due within 3 days");
    expect(releaseRiskLabel(completed, NOW)).toBeNull();
  });

  it("builds bounded factual mission-control counts with KYC evidence", () => {
    const cards = [
      makeCard({ id: "overdue", contact_id: "contact-overdue", reminder_view: "overdue", overdue_task_count: 1 }),
      makeCard({ id: "docs", contact_id: "contact-docs", stage: "documents_pending", document_count: 2, verified_document_count: 1 }),
      makeCard({ id: "sim", contact_id: "contact-sim", stage: "sim_required", owner_user_id: null, owner_name: null }),
      makeCard({ id: "activation", contact_id: "contact-activation", stage: "activation_pending", labels: ["priority"] }),
      makeCard({ id: "done", contact_id: "contact-done", stage: "completed", conversion_indicator: "converted" }),
    ];
    const kycRows = [
      { status: "under_review", checklist_complete: false },
      { status: "approved", checklist_complete: true },
    ] as unknown as KycOperationsResponse["data"];

    const snapshot = buildMissionSnapshot(cards, kycRows, NOW);
    expect(snapshot.active).toBe(4);
    expect(snapshot.overdue).toBe(1);
    expect(snapshot.documentGaps).toBe(1);
    expect(snapshot.pendingKyc).toBe(1);
    expect(snapshot.missingKycEvidence).toBe(1);
    expect(snapshot.simRisk).toBe(1);
    expect(snapshot.activationRisk).toBe(1);
    expect(snapshot.completed).toBe(1);
    expect(snapshot.topAttention[0]?.card.id).toBe("overdue");
  });

  it("does not turn completed cases into operational alerts", () => {
    const completed = makeCard({
      stage: "completed",
      sla_status: "breached",
      reminder_view: "overdue",
      labels: ["priority", "documents_incomplete"],
    });

    expect(urgencyScore(completed, NOW)).toBe(0);
    expect(blockerReasons(completed, NOW)).toEqual([]);
    expect(matchesOperationalView(completed, "attention", NOW)).toBe(false);
  });
});
