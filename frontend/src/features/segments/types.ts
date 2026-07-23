import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Segment = components["schemas"]["SegmentResponse"];
export type SegmentRule = components["schemas"]["SegmentRuleModel"];
export type SegmentCreateRequest = components["schemas"]["SegmentCreateRequest"];
export type SegmentUpdateRequest = components["schemas"]["SegmentUpdateRequest"];
export type SegmentContactsPage = components["schemas"]["SegmentContactsPage"];
export type Contact = components["schemas"]["ContactResponse"];
export type AttributeDefinition = components["schemas"]["AttributeDefinitionResponse"];
export type Tag = components["schemas"]["TagResponse"];

/**
 * The rule grammar, mirrored from `crm/segment_compiler.py`.
 *
 * The contract types every rule field as a plain `str`, so none of this vocabulary can be derived
 * from the generated schema — but the compiler validates against it exactly and answers 422 for
 * anything outside it. Restating it here is what lets the builder offer only rules the server will
 * accept, instead of a free-text form that fails on save.
 *
 * The server re-validates everything; nothing here is trusted.
 */

// --- Field sources -------------------------------------------------------------------------------

export type FieldSource = "contact" | "engagement" | "tag" | "attribute";

export const FIELD_SOURCES: FieldSource[] = ["contact", "engagement", "tag", "attribute"];

export const FIELD_SOURCE_LABELS: Record<FieldSource, string> = {
  contact: "Contact detail",
  engagement: "Engagement",
  tag: "Tag",
  attribute: "Custom attribute",
};

export const FIELD_SOURCE_HINTS: Record<FieldSource, string> = {
  contact: "Who the contact is — name, phone, opt-in status, when they were added.",
  engagement: "When they were last in touch.",
  tag: "Whether they carry a tag.",
  attribute: "One of this organization's own custom fields.",
};

// --- Value types ---------------------------------------------------------------------------------

/** The compiler's own value kinds, plus the attribute-only ones it maps `data_type` onto. */
export type ValueKind = "string" | "boolean" | "datetime" | "number" | "enum";

/** `_OPS_BY_TYPE` and `_ATTR_OPS_BY_TYPE` in the compiler. */
export const OPERATORS_BY_KIND: Record<ValueKind, string[]> = {
  string: ["eq", "ne", "contains", "starts", "ends", "in", "nin", "exists"],
  boolean: ["eq", "exists"],
  datetime: ["eq", "ne", "gt", "gte", "lt", "lte", "between", "exists"],
  number: ["eq", "ne", "gt", "gte", "lt", "lte", "between", "in", "nin", "exists"],
  enum: ["eq", "ne", "in", "nin", "exists"],
};

/** `_TAG_OPS`. */
export const TAG_OPERATORS = ["has_tag", "in", "nin"];

export const OPERATOR_LABELS: Record<string, string> = {
  eq: "is",
  ne: "is not",
  contains: "contains",
  starts: "starts with",
  ends: "ends with",
  in: "is one of",
  nin: "is not one of",
  exists: "is set",
  gt: "is after",
  gte: "is on or after",
  lt: "is before",
  lte: "is on or before",
  between: "is between",
  has_tag: "has tag",
};

/** Numeric comparisons read as before/after for dates but as greater/less for numbers. */
export const NUMERIC_OPERATOR_LABELS: Record<string, string> = {
  ...OPERATOR_LABELS,
  gt: "is greater than",
  gte: "is at least",
  lt: "is less than",
  lte: "is at most",
};

// --- Fields --------------------------------------------------------------------------------------

export interface FieldSpec {
  key: string;
  label: string;
  kind: ValueKind;
  /** A fixed vocabulary the field accepts, where the model defines one. */
  choices?: { value: string; label: string }[];
}

/** `_CONTACT_FIELDS` in the compiler, with the labels an operator would recognise. */
export const CONTACT_FIELDS: FieldSpec[] = [
  { key: "full_name", label: "Full name", kind: "string" },
  { key: "first_name", label: "First name", kind: "string" },
  { key: "last_name", label: "Last name", kind: "string" },
  { key: "email", label: "Email", kind: "string" },
  { key: "phone_e164", label: "Phone (E.164)", kind: "string" },
  { key: "wa_id", label: "WhatsApp id", kind: "string" },
  { key: "country_code", label: "Country code", kind: "string" },
  { key: "locale", label: "Locale", kind: "string" },
  {
    key: "opt_in_status",
    label: "Opt-in status",
    kind: "string",
    // `OPT_IN_STATUSES` on the contact model.
    choices: [
      { value: "opted_in", label: "Opted in" },
      { value: "opted_out", label: "Opted out" },
      { value: "unknown", label: "Unknown" },
    ],
  },
  { key: "source", label: "Source", kind: "string" },
  { key: "is_active_on_wa", label: "Active on WhatsApp", kind: "boolean" },
  { key: "created_at", label: "Added", kind: "datetime" },
];

/** `_ENGAGEMENT_FIELDS`. */
export const ENGAGEMENT_FIELDS: FieldSpec[] = [
  { key: "last_inbound_at", label: "Last inbound message", kind: "datetime" },
  { key: "last_outbound_at", label: "Last outbound message", kind: "datetime" },
  { key: "last_contacted_at", label: "Last contacted", kind: "datetime" },
];

/** The custom-attribute `data_type` values, mapped to the operator set the compiler allows. */
export function kindForDataType(dataType: string): ValueKind {
  if (dataType === "number") return "number";
  if (dataType === "boolean") return "boolean";
  if (dataType === "datetime") return "datetime";
  if (dataType === "enum") return "enum";
  return "string";
}

export function fieldsForSource(
  source: FieldSource,
  attributes: AttributeDefinition[],
): FieldSpec[] {
  if (source === "contact") return CONTACT_FIELDS;
  if (source === "engagement") return ENGAGEMENT_FIELDS;
  if (source === "attribute") {
    return attributes.map((definition) => ({
      key: definition.key_name,
      label: definition.label,
      kind: kindForDataType(definition.data_type),
      choices: definition.enum_values?.map((value) => ({ value, label: value })),
    }));
  }
  // A tag rule's `field_key` is not read by the compiler; it is fixed for clarity in the payload.
  return [{ key: "tags", label: "Tags", kind: "string" }];
}

export function operatorsFor(source: FieldSource, kind: ValueKind): string[] {
  return source === "tag" ? TAG_OPERATORS : OPERATORS_BY_KIND[kind];
}

export function operatorLabel(operator: string, kind: ValueKind): string {
  const table = kind === "number" ? NUMERIC_OPERATOR_LABELS : OPERATOR_LABELS;
  return table[operator] ?? operator;
}

// --- Value shapes ---------------------------------------------------------------------------------

/** How an operator wants its value, which is what decides the control the builder draws. */
export type ValueShape = "none" | "single" | "list" | "range" | "boolean";

export function shapeFor(operator: string): ValueShape {
  if (operator === "exists") return "boolean";
  if (operator === "between") return "range";
  if (operator === "in" || operator === "nin") return "list";
  return "single";
}

// --- Match type -------------------------------------------------------------------------------------

/** `MATCH_TYPES`. */
export const MATCH_TYPES = ["all", "any"] as const;
export type MatchType = (typeof MATCH_TYPES)[number];

export const MATCH_TYPE_LABELS: Record<MatchType, string> = {
  all: "Match all groups",
  any: "Match any group",
};

/**
 * Grouping semantics, straight from the compiler: rules sharing a `group_index` are ANDed, and the
 * resulting groups are combined by `match_type`. Stating it on screen is the only way a builder
 * with two nesting levels is comprehensible.
 */
export const MATCH_TYPE_EXPLANATIONS: Record<MatchType, string> = {
  all: "A contact must satisfy every group. Within a group, every condition must hold.",
  any: "A contact must satisfy at least one group. Within a group, every condition must hold.",
};

// --- Bounds the server enforces ------------------------------------------------------------------------

export const MAX_NAME_LENGTH = 120;
export const MAX_DESCRIPTION_LENGTH = 255;
export const MAX_FIELD_KEY_LENGTH = 60;

/**
 * A segment whose count has never been computed, or whose rules changed since it was.
 *
 * Editing rules or the match type resets `cached_count` and `last_evaluated_at` to null on the
 * server, so "no count" means "not evaluated since the last change" rather than "matches nobody" —
 * and the two must never be shown the same way.
 */
export function isStale(segment: Segment): boolean {
  return segment.cached_count === null || segment.last_evaluated_at === null;
}
