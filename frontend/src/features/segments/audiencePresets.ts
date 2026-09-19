import type { Segment, SegmentCreateRequest, SegmentRule } from "@/features/segments/types";

export const AUDIENCE_PRESET_IDS = [
  "recently_engaged",
  "reactivation_ready",
  "reactivation_eligible",
  "kyc_pending",
  "interested_customers",
  "documents_pending",
  "activation_pending",
  "completed_customers",
  "new_contacts",
  "whatsapp_active",
  "whatsapp_reachable",
  "whatsapp_unreachable",
] as const;

export type AudiencePresetId = (typeof AUDIENCE_PRESET_IDS)[number];

export type SegmentSeed = Pick<
  SegmentCreateRequest,
  "name" | "description" | "match_type" | "rules"
>;

export interface AudiencePreset {
  id: AudiencePresetId;
  label: string;
  shortLabel: string;
  description: string;
  window: string;
}

/**
 * Marketer-facing shortcuts over the segment grammar the API already supports.
 *
 * These are templates, not a second audience engine. Creating one opens the normal segment editor
 * with an ordinary rule payload, so evaluation, tenant isolation and campaign resolution stay on
 * the existing backend path.
 */
export const AUDIENCE_PRESETS: AudiencePreset[] = [
  {
    id: "recently_engaged",
    label: "Recently engaged",
    shortLabel: "Engaged",
    description: "Contacts who sent you a message recently.",
    window: "Last 30 days",
  },
  {
    id: "reactivation_ready",
    label: "Needs reactivation",
    shortLabel: "Reactivation",
    description: "Previously contacted people who have been inactive.",
    window: "Inactive 30+ days",
  },
  {
    id: "reactivation_eligible",
    label: "Eligible for reactivation",
    shortLabel: "Eligible",
    description: "Contacts whose latest eligibility decision is eligible.",
    window: "Latest decision",
  },
  {
    id: "kyc_pending",
    label: "KYC in progress",
    shortLabel: "KYC pending",
    description: "Contacts whose KYC is pending, awaiting documents or under review.",
    window: "Current KYC status",
  },
  {
    id: "interested_customers",
    label: "Interested customers",
    shortLabel: "Interested",
    description: "Contacts at the lead-confirmed reactivation stage.",
    window: "Current CRM stage",
  },
  {
    id: "documents_pending",
    label: "Documents pending",
    shortLabel: "Docs pending",
    description: "Contacts whose current reactivation stage is waiting for documents.",
    window: "Current CRM stage",
  },
  {
    id: "activation_pending",
    label: "Activation in progress",
    shortLabel: "Activation",
    description: "Contacts with an activation still moving toward completion.",
    window: "Current activation status",
  },
  {
    id: "completed_customers",
    label: "Completed customers",
    shortLabel: "Completed",
    description: "Contacts whose reactivation case is complete.",
    window: "Current CRM stage",
  },
  {
    id: "new_contacts",
    label: "New contacts",
    shortLabel: "New",
    description: "Contacts added to your workspace recently.",
    window: "Added in 7 days",
  },
  {
    id: "whatsapp_active",
    label: "WhatsApp active",
    shortLabel: "WhatsApp active",
    description: "Contacts who have written to us, so we know they are live on WhatsApp.",
    window: "Current status",
  },
  {
    id: "whatsapp_reachable",
    label: "Reachable on WhatsApp",
    shortLabel: "Reachable",
    description: "Meta delivered a campaign message to them — a wider set than those who replied.",
    window: "Delivery evidence",
  },
  {
    id: "whatsapp_unreachable",
    label: "Not on WhatsApp",
    shortLabel: "Not on WhatsApp",
    description: "Meta refused these numbers. Exclude them and stop paying for the same refusal.",
    window: "Delivery evidence",
  },
];

const DAY_MS = 24 * 60 * 60 * 1000;

function daysAgo(now: Date, days: number): string {
  const cutoff = new Date(now.getTime() - days * DAY_MS);
  cutoff.setMilliseconds(0);
  return cutoff.toISOString();
}

function dateOnly(value: string): string {
  return value.slice(0, 10);
}

function rule(
  fieldSource: SegmentRule["field_source"],
  fieldKey: string,
  operator: string,
  value: SegmentRule["value"],
): SegmentRule {
  return {
    group_index: 0,
    field_source: fieldSource,
    field_key: fieldKey,
    operator,
    value,
  };
}

export function isAudiencePresetId(value: unknown): value is AudiencePresetId {
  return AUDIENCE_PRESET_IDS.includes(value as AudiencePresetId);
}

/** Build a normal segment draft. Date thresholds are deliberately visible and editable. */
export function createAudiencePresetSeed(id: AudiencePresetId, now = new Date()): SegmentSeed {
  if (id === "recently_engaged") {
    const cutoff = daysAgo(now, 30);
    return {
      name: "Recently engaged — last 30 days",
      description: `Sent an inbound message on or after ${dateOnly(cutoff)}. Threshold set when created.`,
      match_type: "all",
      rules: [rule("engagement", "last_inbound_at", "gte", cutoff)],
    };
  }

  if (id === "reactivation_ready") {
    const cutoff = daysAgo(now, 30);
    return {
      name: "Needs reactivation — 30+ days",
      description: `Last contacted on or before ${dateOnly(cutoff)}. Threshold set when created.`,
      match_type: "all",
      rules: [rule("engagement", "last_contacted_at", "lte", cutoff)],
    };
  }

  if (id === "reactivation_eligible") {
    return {
      name: "Eligible for reactivation",
      description: "Latest recorded eligibility decision is eligible.",
      match_type: "all",
      rules: [rule("reactivation", "eligibility_status", "eq", "eligible")],
    };
  }

  if (id === "kyc_pending") {
    return {
      name: "KYC in progress",
      description: "Current KYC status is pending, documents pending or under review.",
      match_type: "all",
      rules: [
        rule("kyc", "status", "in", ["pending", "documents_pending", "under_review"]),
      ],
    };
  }

  if (id === "interested_customers") {
    return {
      name: "Interested customers",
      description: "Current reactivation stage is lead confirmed.",
      match_type: "all",
      rules: [rule("reactivation", "stage", "eq", "lead_confirmed")],
    };
  }

  if (id === "documents_pending") {
    return {
      name: "Documents pending",
      description: "Current reactivation stage is documents pending.",
      match_type: "all",
      rules: [rule("reactivation", "stage", "eq", "documents_pending")],
    };
  }

  if (id === "activation_pending") {
    return {
      name: "Activation in progress",
      description: "Current activation has not completed or been rejected.",
      match_type: "all",
      rules: [
        rule("activation", "status", "in", ["pending", "verification", "ready", "approved"]),
      ],
    };
  }

  if (id === "completed_customers") {
    return {
      name: "Completed customers",
      description: "Current reactivation stage is completed.",
      match_type: "all",
      rules: [rule("reactivation", "stage", "eq", "completed")],
    };
  }

  if (id === "new_contacts") {
    const cutoff = daysAgo(now, 7);
    return {
      name: "New contacts — last 7 days",
      description: `Added on or after ${dateOnly(cutoff)}. Threshold set when created.`,
      match_type: "all",
      rules: [rule("contact", "created_at", "gte", cutoff)],
    };
  }

  if (id === "whatsapp_reachable") {
    return {
      name: "Reachable on WhatsApp",
      description:
        "Meta delivered a campaign message to them. Read from delivery receipts — nothing is " +
        "sent to find out.",
      match_type: "all",
      rules: [rule("scan", "reachability", "eq", "reachable")],
    };
  }

  if (id === "whatsapp_unreachable") {
    return {
      name: "Not on WhatsApp",
      description:
        "Meta refused these numbers as not WhatsApp users (error 131026). Excluding them stops " +
        "paying for the same refusal every campaign.",
      match_type: "all",
      rules: [rule("scan", "reachability", "eq", "unreachable")],
    };
  }

  return {
    name: "WhatsApp active contacts",
    description: "Contacts who have written to us, so we know they are live on WhatsApp.",
    match_type: "all",
    rules: [rule("contact", "is_active_on_wa", "eq", true)],
  };
}

/**
 * Recognise a saved segment's broad intent for campaign quick-picks. The actual segment remains the
 * selected audience; this label never changes or reinterprets its rule payload.
 */
export function audiencePresetIdForSegment(
  segment: Pick<Segment, "rules">,
): AudiencePresetId | null {
  for (const candidate of segment.rules) {
    if (
      candidate.field_source === "engagement" &&
      candidate.field_key === "last_inbound_at" &&
      (candidate.operator === "gte" || candidate.operator === "gt")
    ) {
      return "recently_engaged";
    }
    if (
      candidate.field_source === "engagement" &&
      candidate.field_key === "last_contacted_at" &&
      (candidate.operator === "lte" || candidate.operator === "lt")
    ) {
      return "reactivation_ready";
    }
    if (
      candidate.field_source === "reactivation" &&
      candidate.field_key === "eligibility_status" &&
      candidate.operator === "eq" &&
      candidate.value === "eligible"
    ) {
      return "reactivation_eligible";
    }
    if (
      candidate.field_source === "kyc" &&
      candidate.field_key === "status" &&
      candidate.operator === "in" &&
      sameValues(candidate.value, ["pending", "documents_pending", "under_review"])
    ) {
      return "kyc_pending";
    }
    if (
      candidate.field_source === "reactivation" &&
      candidate.field_key === "stage" &&
      candidate.operator === "eq" &&
      candidate.value === "lead_confirmed"
    ) {
      return "interested_customers";
    }
    if (
      candidate.field_source === "reactivation" &&
      candidate.field_key === "stage" &&
      candidate.operator === "eq" &&
      candidate.value === "documents_pending"
    ) {
      return "documents_pending";
    }
    if (
      candidate.field_source === "activation" &&
      candidate.field_key === "status" &&
      candidate.operator === "in" &&
      sameValues(candidate.value, ["pending", "verification", "ready", "approved"])
    ) {
      return "activation_pending";
    }
    if (
      candidate.field_source === "reactivation" &&
      candidate.field_key === "stage" &&
      candidate.operator === "eq" &&
      candidate.value === "completed"
    ) {
      return "completed_customers";
    }
    if (
      candidate.field_source === "contact" &&
      candidate.field_key === "created_at" &&
      (candidate.operator === "gte" || candidate.operator === "gt")
    ) {
      return "new_contacts";
    }
    if (
      candidate.field_source === "contact" &&
      candidate.field_key === "is_active_on_wa" &&
      candidate.operator === "eq" &&
      candidate.value === true
    ) {
      return "whatsapp_active";
    }
  }
  return null;
}

function sameValues(value: SegmentRule["value"], expected: string[]): boolean {
  return (
    Array.isArray(value) &&
    value.length === expected.length &&
    expected.every((entry) => value.includes(entry))
  );
}

export function audiencePresetById(id: AudiencePresetId): AudiencePreset {
  return AUDIENCE_PRESETS.find((preset) => preset.id === id)!;
}
