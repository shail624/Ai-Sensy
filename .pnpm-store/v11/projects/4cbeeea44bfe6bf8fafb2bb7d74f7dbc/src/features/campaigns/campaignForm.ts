import { z } from "zod";

import { MAPPABLE_FIELDS } from "@/features/campaigns/templateShape";
import type {
  AudienceType,
  Campaign,
  CampaignCreateRequest,
  CampaignUpdateRequest,
} from "@/features/campaigns/types";

const MAPPABLE_KEYS = MAPPABLE_FIELDS.map((field) => field.value);

/**
 * One variable mapping. The rules mirror the server's `_validate_mapping` so the operator is told
 * what is wrong before a round trip; the server re-checks all of it and its 422 is authoritative.
 */
const mappingSchema = z
  .object({
    source: z.enum(["field", "attribute", "literal"]),
    key: z.string(),
    value: z.string(),
    fallback: z.string(),
  })
  .superRefine((mapping, ctx) => {
    if (mapping.source === "field" && !MAPPABLE_KEYS.includes(mapping.key)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["key"], message: "Choose a contact field" });
    }
    if (mapping.source === "attribute" && mapping.key.trim() === "") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["key"], message: "Choose an attribute" });
    }
    if (mapping.source === "literal" && mapping.value.trim() === "") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["value"], message: "Enter a value" });
    }
  });

export type MappingValues = z.infer<typeof mappingSchema>;

/**
 * `upload` is deliberately absent: the server refuses it outright ("upload audiences must be
 * imported into contacts first, then targeted by tag or segment"), so offering it would only build
 * a campaign that cannot resolve an audience.
 */
export const SELECTABLE_AUDIENCE_TYPES: AudienceType[] = ["segment", "tag", "list"];

// `name` ≤160 matches the server's own bound (Doc 04 §17), so over-long input fails here first.
export const campaignSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(160, "Name is too long"),
    phone_number_id: z.string().min(1, "Choose a sending number"),
    template_id: z.string().min(1, "Choose a template"),
    audience_type: z.enum(["segment", "tag", "list"]),
    segment_id: z.string(),
    tag_ids: z.array(z.string()),
    contact_ids: z.array(z.string()),
    header: z.array(mappingSchema),
    body: z.array(mappingSchema),
  })
  .superRefine((values, ctx) => {
    if (values.audience_type === "segment" && values.segment_id === "") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["segment_id"],
        message: "Choose a segment",
      });
    }
    if (values.audience_type === "tag" && values.tag_ids.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["tag_ids"],
        message: "Choose at least one tag",
      });
    }
    if (values.audience_type === "list" && values.contact_ids.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["contact_ids"],
        message: "Choose at least one contact",
      });
    }
  });

export type CampaignFormValues = z.infer<typeof campaignSchema>;

export function emptyMapping(): MappingValues {
  return { source: "field", key: "full_name", value: "", fallback: "" };
}

export function blankCampaign(): CampaignFormValues {
  return {
    name: "",
    phone_number_id: "",
    template_id: "",
    audience_type: "segment",
    segment_id: "",
    tag_ids: [],
    contact_ids: [],
    header: [],
    body: [],
  };
}

/**
 * A new campaign aimed at an explicit set of contacts — the `list` audience the contract already
 * models (`AudienceRef.contact_ids`). Used when the contacts list hands a selection to the wizard,
 * so audience composition keeps one implementation.
 */
export function contactsToForm(contactIds: string[]): CampaignFormValues {
  return { ...blankCampaign(), audience_type: "list", contact_ids: contactIds };
}

/** Read a stored mapping list back into form values, tolerating anything unexpected. */
function toMappings(raw: unknown): MappingValues[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const mapping = (entry ?? {}) as Partial<Record<keyof MappingValues, unknown>>;
    const source = mapping.source;
    return {
      source: source === "attribute" || source === "literal" ? source : "field",
      key: typeof mapping.key === "string" ? mapping.key : "",
      value: typeof mapping.value === "string" ? mapping.value : "",
      fallback: typeof mapping.fallback === "string" ? mapping.fallback : "",
    };
  });
}

function toIdList(raw: unknown): string[] {
  return Array.isArray(raw) ? raw.filter((entry): entry is string => typeof entry === "string") : [];
}

/**
 * Form values from an existing campaign — used both by edit and by duplicate.
 *
 * `audience_ref` and `variable_map` are typed as free-form objects on the wire, so their interiors
 * are read defensively: a campaign written by an older shape loads with the parts that still make
 * sense rather than failing to open.
 */
export function campaignToForm(campaign: Campaign): CampaignFormValues {
  const ref = (campaign.audience_ref ?? {}) as Record<string, unknown>;
  const map = (campaign.variable_map ?? {}) as Record<string, unknown>;
  const audienceType = SELECTABLE_AUDIENCE_TYPES.includes(campaign.audience_type as AudienceType)
    ? (campaign.audience_type as CampaignFormValues["audience_type"])
    : "segment";

  return {
    name: campaign.name,
    phone_number_id: campaign.phone_number_id,
    template_id: campaign.template_id,
    audience_type: audienceType,
    segment_id: typeof ref.segment_id === "string" ? ref.segment_id : "",
    tag_ids: toIdList(ref.tag_ids),
    contact_ids: toIdList(ref.contact_ids),
    header: toMappings(map.header),
    body: toMappings(map.body),
  };
}

/** A duplicate is the source campaign's definition under a new name, as a fresh draft. */
export function duplicateToForm(campaign: Campaign): CampaignFormValues {
  return { ...campaignToForm(campaign), name: `${campaign.name} (copy)` };
}

/** A governed follow-up starts as a fresh draft with the source definition and a distinct name. */
export function followUpToForm(campaign: Campaign): CampaignFormValues {
  return { ...campaignToForm(campaign), name: `${campaign.name} — follow-up` };
}

/**
 * Only the audience keys the chosen type actually uses are sent. Carrying a stale `segment_id`
 * alongside a tag audience would leave the campaign describing an audience it does not target.
 */
function toAudienceRef(values: CampaignFormValues): CampaignCreateRequest["audience_ref"] {
  if (values.audience_type === "segment") return { segment_id: values.segment_id };
  if (values.audience_type === "tag") return { tag_ids: values.tag_ids };
  return { contact_ids: values.contact_ids };
}

function toVariableMap(values: CampaignFormValues): CampaignCreateRequest["variable_map"] {
  const clean = (mappings: MappingValues[]) =>
    mappings.map((mapping) => ({
      source: mapping.source,
      key: mapping.source === "literal" ? null : mapping.key,
      value: mapping.source === "literal" ? mapping.value : null,
      fallback: mapping.fallback.trim() === "" ? null : mapping.fallback,
    }));
  return { header: clean(values.header), body: clean(values.body) };
}

export function toCreateRequest(values: CampaignFormValues): CampaignCreateRequest {
  return {
    name: values.name.trim(),
    phone_number_id: values.phone_number_id,
    template_id: values.template_id,
    audience_type: values.audience_type,
    audience_ref: toAudienceRef(values),
    variable_map: toVariableMap(values),
  };
}

/**
 * The full definition plus `row_version`, so a concurrent edit surfaces as the server's conflict
 * rather than silently overwriting someone else's change.
 */
export function toUpdateRequest(
  values: CampaignFormValues,
  rowVersion: number,
): CampaignUpdateRequest {
  return { ...toCreateRequest(values), row_version: rowVersion };
}
