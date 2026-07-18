import type { AttributeDefinition, SegmentRule, Tag } from "@/features/contacts/types";

export interface ContactFilters {
  /** Free-text search (matched against name, or phone when it looks numeric). */
  search: string;
  /** Selected tag id ("" = none). */
  tagId: string;
  /** Custom-attribute filters: `key_name` → selected enum value ("" = none). */
  attributes: Record<string, string>;
}

export const emptyFilters: ContactFilters = { search: "", tagId: "", attributes: {} };

export function hasActiveFilters(filters: ContactFilters): boolean {
  return (
    filters.search.trim() !== "" ||
    filters.tagId !== "" ||
    Object.values(filters.attributes).some((value) => value !== "")
  );
}

/**
 * Build `ContactSearchRequest.rules` from filter state, using only the segment-rule vocabulary the
 * backend accepts (Doc 03 §6.4 / `segment_compiler`): `field_source` contact/tag/attribute, and the
 * `contains` / `has_tag` / `eq` operators. Each control is its own group; groups are ANDed
 * (`match_type: "all"`).
 *
 * Search is single-field because the flat group/`match_type` model cannot express
 * "(name OR phone) AND filters" — so a numeric query matches `phone_e164`, otherwise `full_name`.
 */
export function buildRules(
  filters: ContactFilters,
  tags: Tag[],
  definitions: AttributeDefinition[],
): SegmentRule[] {
  const rules: SegmentRule[] = [];
  let group = 0;

  const query = filters.search.trim();
  if (query) {
    const field = /\d/.test(query) ? "phone_e164" : "full_name";
    rules.push({
      group_index: group++,
      field_source: "contact",
      field_key: field,
      operator: "contains",
      value: query,
    });
  }

  if (filters.tagId) {
    const tag = tags.find((candidate) => candidate.id === filters.tagId);
    if (tag) {
      // Tag rules match by name (`has_tag`); `field_key` is unused by the backend for tag rules.
      rules.push({
        group_index: group++,
        field_source: "tag",
        field_key: "tags",
        operator: "has_tag",
        value: tag.name,
      });
    }
  }

  for (const [key, value] of Object.entries(filters.attributes)) {
    if (!value) continue;
    if (definitions.some((def) => def.key_name === key)) {
      rules.push({
        group_index: group++,
        field_source: "attribute",
        field_key: key,
        operator: "eq",
        value,
      });
    }
  }

  return rules;
}
