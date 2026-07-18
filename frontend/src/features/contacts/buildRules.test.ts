import { describe, expect, it } from "vitest";

import { buildRules, emptyFilters, hasActiveFilters } from "@/features/contacts/buildRules";
import type { AttributeDefinition, Tag } from "@/features/contacts/types";

function tagFixture(): Tag {
  return {
    id: "t1",
    type: "tag",
    name: "vip",
    color: null,
    description: null,
    usage_count: 0,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  };
}

function attrFixture(): AttributeDefinition {
  return {
    id: "a1",
    type: "attribute",
    key_name: "reactivation_status",
    label: "Reactivation Status",
    data_type: "enum",
    enum_values: ["pending", "done"],
    is_indexed: false,
    is_pii: false,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  };
}

const tags = [tagFixture()];
const defs = [attrFixture()];

describe("buildRules", () => {
  it("returns no rules for empty filters", () => {
    expect(buildRules(emptyFilters, tags, defs)).toEqual([]);
    expect(hasActiveFilters(emptyFilters)).toBe(false);
  });

  it("builds a name-contains rule for a text query", () => {
    expect(buildRules({ ...emptyFilters, search: "Priya" }, tags, defs)).toEqual([
      { group_index: 0, field_source: "contact", field_key: "full_name", operator: "contains", value: "Priya" },
    ]);
  });

  it("searches phone for a numeric query", () => {
    const rules = buildRules({ ...emptyFilters, search: "98765" }, tags, defs);
    expect(rules[0]?.field_key).toBe("phone_e164");
  });

  it("builds a has_tag rule using the tag name", () => {
    expect(buildRules({ ...emptyFilters, tagId: "t1" }, tags, defs)).toEqual([
      { group_index: 0, field_source: "tag", field_key: "tags", operator: "has_tag", value: "vip" },
    ]);
  });

  it("builds an attribute eq rule", () => {
    expect(
      buildRules({ ...emptyFilters, attributes: { reactivation_status: "pending" } }, tags, defs),
    ).toEqual([
      { group_index: 0, field_source: "attribute", field_key: "reactivation_status", operator: "eq", value: "pending" },
    ]);
  });

  it("combines controls as separate AND groups", () => {
    const rules = buildRules(
      { search: "Priya", tagId: "t1", attributes: { reactivation_status: "pending" } },
      tags,
      defs,
    );
    expect(rules.map((rule) => rule.group_index)).toEqual([0, 1, 2]);
    expect(hasActiveFilters({ search: "Priya", tagId: "", attributes: {} })).toBe(true);
  });

  it("ignores an unknown attribute key", () => {
    expect(buildRules({ ...emptyFilters, attributes: { unknown: "x" } }, tags, defs)).toEqual([]);
  });
});
