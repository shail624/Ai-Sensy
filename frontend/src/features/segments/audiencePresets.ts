import type { Segment, SegmentCreateRequest, SegmentRule } from "@/features/segments/types";

export const AUDIENCE_PRESET_IDS = [
  "recently_engaged",
  "reactivation_ready",
  "new_contacts",
  "whatsapp_active",
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
    description: "Contacts currently marked active on WhatsApp.",
    window: "Current status",
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

  if (id === "new_contacts") {
    const cutoff = daysAgo(now, 7);
    return {
      name: "New contacts — last 7 days",
      description: `Added on or after ${dateOnly(cutoff)}. Threshold set when created.`,
      match_type: "all",
      rules: [rule("contact", "created_at", "gte", cutoff)],
    };
  }

  return {
    name: "WhatsApp active contacts",
    description: "Contacts currently marked active on WhatsApp.",
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

export function audiencePresetById(id: AudiencePresetId): AudiencePreset {
  return AUDIENCE_PRESETS.find((preset) => preset.id === id)!;
}
