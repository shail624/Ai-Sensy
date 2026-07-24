import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { RuleBuilder, blankRule, defaultValueFor } from "@/features/segments/RuleBuilder";
import { RuleSummary } from "@/features/segments/RuleSummary";
import { SegmentActions } from "@/features/segments/SegmentActions";
import { CountChip, RuleCountChip } from "@/features/segments/SegmentBadges";
import { SegmentDetail } from "@/features/segments/SegmentDetail";
import { SegmentEditor } from "@/features/segments/SegmentEditor";
import { SegmentList } from "@/features/segments/SegmentList";
import type { RuleGroup, SegmentListQuery } from "@/features/segments/selectors";
import {
  DEFAULT_LIST_QUERY,
  filterSegments,
  flattenGroups,
  groupRules,
  hasProblems,
  matchesSearch,
  PAGE_SIZE,
  segmentSummary,
  selectSegmentPage,
  validateSegment,
} from "@/features/segments/selectors";
import type { AttributeDefinition, Segment, SegmentRule, Tag } from "@/features/segments/types";
import {
  fieldsForSource,
  isStale,
  kindForDataType,
  operatorsFor,
  shapeFor,
} from "@/features/segments/types";

// --- Fixtures -----------------------------------------------------------------------------------

function ruleFixture(overrides: Partial<SegmentRule> = {}): SegmentRule {
  return {
    group_index: 0,
    field_source: "contact",
    field_key: "full_name",
    operator: "contains",
    value: "Priya",
    ...overrides,
  };
}

function segmentFixture(overrides: Partial<Segment> = {}): Segment {
  return {
    id: "s1",
    type: "segment",
    name: "Lapsed customers",
    description: "No inbound message in 90 days.",
    match_type: "all",
    rules: [ruleFixture()],
    is_dynamic: true,
    cached_count: 1240,
    last_evaluated_at: "2026-07-22T09:00:00Z",
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function attributeFixture(overrides: Partial<AttributeDefinition> = {}): AttributeDefinition {
  return {
    id: "a1",
    type: "attribute_definition",
    key_name: "plan",
    label: "Plan",
    data_type: "enum",
    enum_values: ["basic", "premium"],
    is_indexed: true,
    is_pii: false,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

function tagFixture(overrides: Partial<Tag> = {}): Tag {
  return {
    id: "t1",
    type: "tag",
    name: "vip",
    color: null,
    description: null,
    usage_count: 12,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = { value: ["segments:read", "segments:write"] };

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigate };
});

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};
const writes: { path: string; body: unknown }[] = [];

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async (path: string, init?: { body?: unknown }) => {
    writes.push({ path, body: init?.body });
    return path in responses
      ? { data: responses[path] }
      : { error: { detail: "network disabled under test" } };
  };
  return {
    api: { GET: get, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function query(overrides: Partial<SegmentListQuery> = {}): SegmentListQuery {
  return { ...DEFAULT_LIST_QUERY, ...overrides };
}

/** The catalogs the editor needs; seeded by default so the builder renders. */
function seedCatalogs(): void {
  responses["/api/v1/custom-attributes"] = [attributeFixture()];
  responses["/api/v1/tags"] = [tagFixture()];
}

beforeEach(() => {
  permissions.value = ["segments:read", "segments:write"];
  for (const key of Object.keys(responses)) delete responses[key];
  writes.length = 0;
  navigate.mockClear();
});

// --- Rule grammar ------------------------------------------------------------------------------------

describe("rule grammar", () => {
  it("offers each source only the fields the compiler knows", () => {
    expect(fieldsForSource("contact", []).map((f) => f.key)).toContain("opt_in_status");
    expect(fieldsForSource("engagement", []).map((f) => f.key)).toEqual([
      "last_inbound_at",
      "last_outbound_at",
      "last_contacted_at",
    ]);
    expect(fieldsForSource("attribute", [attributeFixture()]).map((f) => f.key)).toEqual(["plan"]);
    expect(fieldsForSource("tag", []).map((f) => f.key)).toEqual(["tags"]);
  });

  it("offers each field type only the operators the compiler accepts", () => {
    expect(operatorsFor("contact", "string")).toEqual([
      "eq", "ne", "contains", "starts", "ends", "in", "nin", "exists",
    ]);
    expect(operatorsFor("contact", "boolean")).toEqual(["eq", "exists"]);
    expect(operatorsFor("contact", "datetime")).toContain("between");
    // A boolean field must never be offered `contains`.
    expect(operatorsFor("contact", "boolean")).not.toContain("contains");
    expect(operatorsFor("tag", "string")).toEqual(["has_tag", "in", "nin"]);
    // Enum attributes have no substring operators.
    expect(operatorsFor("attribute", "enum")).toEqual(["eq", "ne", "in", "nin", "exists"]);
  });

  it("maps each attribute data_type to its operator set", () => {
    expect(kindForDataType("number")).toBe("number");
    expect(kindForDataType("boolean")).toBe("boolean");
    expect(kindForDataType("datetime")).toBe("datetime");
    expect(kindForDataType("enum")).toBe("enum");
    expect(kindForDataType("string")).toBe("string");
    expect(kindForDataType("something_new")).toBe("string");
  });

  it("knows what shape each operator's value takes", () => {
    expect(shapeFor("exists")).toBe("boolean");
    expect(shapeFor("between")).toBe("range");
    expect(shapeFor("in")).toBe("list");
    expect(shapeFor("nin")).toBe("list");
    expect(shapeFor("eq")).toBe("single");
  });

  it("gives a new rule a value its operator will accept", () => {
    expect(defaultValueFor("exists")).toBe(true);
    expect(defaultValueFor("between")).toEqual(["", ""]);
    expect(defaultValueFor("in")).toEqual([]);
    expect(defaultValueFor("eq")).toBe("");
  });

  it("builds a blank rule that is already valid for its source", () => {
    const rule = blankRule("tag", []);
    expect(rule.field_source).toBe("tag");
    expect(operatorsFor("tag", "string")).toContain(rule.operator);
  });
});

// --- Grouping ------------------------------------------------------------------------------------------

describe("rule grouping", () => {
  it("groups rules by group_index, in order", () => {
    const groups = groupRules([
      ruleFixture({ group_index: 1, field_key: "email" }),
      ruleFixture({ group_index: 0 }),
      ruleFixture({ group_index: 1, field_key: "locale" }),
    ]);
    expect(groups.map((g) => g.index)).toEqual([0, 1]);
    expect(groups[1]?.rules).toHaveLength(2);
  });

  it("renumbers on flatten, so a deleted group leaves no gap", () => {
    const groups: RuleGroup[] = [
      { index: 0, rules: [] },
      { index: 5, rules: [ruleFixture()] },
      { index: 9, rules: [ruleFixture({ field_key: "email" })] },
    ];
    // An empty group is dropped and the survivors renumber from zero — a gap would change which
    // rules the compiler ANDs together.
    expect(flattenGroups(groups).map((r) => r.group_index)).toEqual([0, 1]);
  });

  it("round-trips a rule set unchanged", () => {
    const rules = [
      ruleFixture({ group_index: 0 }),
      ruleFixture({ group_index: 1, field_key: "email", operator: "eq", value: "a@b.com" }),
    ];
    expect(flattenGroups(groupRules(rules))).toEqual(rules);
  });
});

// --- Validation ----------------------------------------------------------------------------------------

describe("validateSegment", () => {
  const attributes = [attributeFixture()];

  function draft(rules: SegmentRule[]): RuleGroup[] {
    return [{ index: 0, rules }];
  }

  it("requires a name and bounds both text fields", () => {
    expect(validateSegment("", "", [], attributes).name).toMatch(/required/);
    expect(validateSegment("x".repeat(121), "", [], attributes).name).toMatch(/120 characters/);
    expect(validateSegment("ok", "y".repeat(256), [], attributes).description).toMatch(/255/);
  });

  it("accepts a segment with no rules, because the backend does", () => {
    // It matches everyone — a dangerous thing to save, but a legal one. The editor warns instead.
    expect(hasProblems(validateSegment("Everyone", "", [], attributes))).toBe(false);
  });

  it("rejects an operator the field's type does not support", () => {
    const problems = validateSegment(
      "n",
      "",
      draft([ruleFixture({ field_key: "is_active_on_wa", operator: "contains", value: "x" })]),
      attributes,
    );
    expect(problems.rules["0:0"]).toMatch(/does not apply/);
  });

  it("requires a value, and the right kind of value", () => {
    expect(
      validateSegment("n", "", draft([ruleFixture({ value: "" })]), attributes).rules["0:0"],
    ).toMatch(/Enter a value/);

    expect(
      validateSegment("n", "", draft([ruleFixture({ operator: "in", value: [] })]), attributes)
        .rules["0:0"],
    ).toMatch(/at least one value/);

    expect(
      validateSegment(
        "n",
        "",
        draft([ruleFixture({ field_key: "created_at", operator: "between", value: ["2026-01-01"] })]),
        attributes,
      ).rules["0:0"],
    ).toMatch(/both ends/);

    expect(
      validateSegment(
        "n",
        "",
        draft([ruleFixture({ field_key: "is_active_on_wa", operator: "exists", value: "yes" })]),
        attributes,
      ).rules["0:0"],
    ).toMatch(/yes or no/);
  });

  it("rejects an unknown custom attribute", () => {
    const problems = validateSegment(
      "n",
      "",
      draft([ruleFixture({ field_source: "attribute", field_key: "gone", operator: "eq", value: "x" })]),
      attributes,
    );
    expect(problems.rules["0:0"]).toMatch(/Choose a custom attribute/);
  });

  it("accepts a well-formed rule set", () => {
    const problems = validateSegment(
      "Lapsed",
      "desc",
      draft([
        ruleFixture(),
        ruleFixture({ field_source: "tag", field_key: "tags", operator: "has_tag", value: "vip" }),
      ]),
      attributes,
    );
    expect(hasProblems(problems)).toBe(false);
  });

  it("keys each problem to the row that caused it", () => {
    const groups: RuleGroup[] = [
      { index: 0, rules: [ruleFixture()] },
      { index: 1, rules: [ruleFixture({ value: "" })] },
    ];
    const problems = validateSegment("n", "", groups, attributes);
    expect(problems.rules["0:0"]).toBeUndefined();
    expect(problems.rules["1:0"]).toBeDefined();
  });
});

// --- List selectors ----------------------------------------------------------------------------------------

describe("selectors — list", () => {
  const rows = [
    segmentFixture({ id: "a", name: "Alpha", cached_count: 10, match_type: "all" }),
    segmentFixture({ id: "b", name: "Bravo", cached_count: null, last_evaluated_at: null, match_type: "any" }),
    segmentFixture({ id: "c", name: "Charlie", cached_count: 0, description: "empty one" }),
  ];

  it("searches name and description", () => {
    expect(matchesSearch(rows[0]!, "alph")).toBe(true);
    expect(matchesSearch(rows[2]!, "empty")).toBe(true);
    expect(matchesSearch(rows[0]!, "  ")).toBe(true);
    expect(matchesSearch(rows[0]!, "nothing")).toBe(false);
  });

  it("separates never-evaluated from matches-nobody", () => {
    // Two very different statements; a filter that conflated them would mislead before a campaign.
    expect(filterSegments(rows, query({ state: "stale" })).map((r) => r.id)).toEqual(["b"]);
    expect(filterSegments(rows, query({ state: "empty" })).map((r) => r.id)).toEqual(["c"]);
    expect(filterSegments(rows, query({ state: "evaluated" })).map((r) => r.id)).toEqual(["a", "c"]);
  });

  it("filters by match type", () => {
    expect(filterSegments(rows, query({ match: "any" })).map((r) => r.id)).toEqual(["b"]);
  });

  it("sorts a never-evaluated segment last by size, not first", () => {
    const sorted = selectSegmentPage(rows, query({ sort: "-cached_count" })).rows;
    expect(sorted[sorted.length - 1]?.id).toBe("b");
  });

  it("clamps a page past the end and slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 3 }, (_, index) =>
      segmentFixture({ id: `s${index}`, name: `Segment ${index}` }),
    );
    expect(selectSegmentPage(many, query()).rows).toHaveLength(PAGE_SIZE);
    expect(selectSegmentPage(many, query({ page: 2 })).rows).toHaveLength(3);
    expect(selectSegmentPage(many, query({ page: 99 })).page).toBe(2);
  });

  it("summarises evaluated and awaiting-evaluation counts", () => {
    expect(segmentSummary(rows)).toEqual({ total: 3, evaluated: 2, stale: 1, reach: 10 });
  });

  it("treats a missing count or timestamp as un-evaluated", () => {
    expect(isStale(segmentFixture({ cached_count: null }))).toBe(true);
    expect(isStale(segmentFixture({ last_evaluated_at: null }))).toBe(true);
    expect(isStale(segmentFixture())).toBe(false);
  });
});

// --- Badges -------------------------------------------------------------------------------------------------

describe("SegmentBadges", () => {
  it("never renders an un-evaluated segment as zero contacts", () => {
    withProviders(<CountChip segment={segmentFixture({ cached_count: null, last_evaluated_at: null })} />);
    expect(screen.getByText("Not evaluated")).toBeInTheDocument();
    expect(screen.queryByText(/0 contacts/)).not.toBeInTheDocument();
  });

  it("renders an evaluated count", () => {
    withProviders(<CountChip segment={segmentFixture({ cached_count: 1 })} />);
    expect(screen.getByText("1 contact")).toBeInTheDocument();
  });

  it("warns that a segment with no conditions matches everyone", () => {
    withProviders(<RuleCountChip count={0} />);
    expect(screen.getByText("No conditions")).toBeInTheDocument();
  });
});

// --- RuleSummary ---------------------------------------------------------------------------------------------

describe("RuleSummary", () => {
  it("reads a rule back as a sentence", () => {
    withProviders(
      <RuleSummary rules={[ruleFixture()]} matchType="all" attributes={[]} />,
    );
    expect(screen.getByText("Full name")).toBeInTheDocument();
    expect(screen.getByText("contains")).toBeInTheDocument();
    expect(screen.getByText("Priya")).toBeInTheDocument();
  });

  it("joins groups with the match type and conditions with and", () => {
    withProviders(
      <RuleSummary
        rules={[
          ruleFixture({ group_index: 0 }),
          ruleFixture({ group_index: 0, field_key: "email", operator: "exists", value: true }),
          ruleFixture({ group_index: 1, field_key: "locale", operator: "eq", value: "en" }),
        ]}
        matchType="any"
        attributes={[]}
      />,
    );
    expect(screen.getByText("OR")).toBeInTheDocument();
    expect(screen.getByText("and")).toBeInTheDocument();
  });

  it("says a segment with no conditions matches everyone", () => {
    withProviders(<RuleSummary rules={[]} matchType="all" attributes={[]} />);
    expect(screen.getByText(/matches every contact/)).toBeInTheDocument();
  });
});

// --- RuleBuilder ---------------------------------------------------------------------------------------------

describe("RuleBuilder", () => {
  function renderBuilder(groups: RuleGroup[]) {
    const onChange = vi.fn();
    withProviders(
      <RuleBuilder
        groups={groups}
        onChange={onChange}
        attributes={[attributeFixture()]}
        tags={[tagFixture()]}
        matchType="all"
        problems={{}}
      />,
    );
    return onChange;
  }

  it("constrains the operator list to the chosen field's type", () => {
    renderBuilder([{ index: 0, rules: [ruleFixture({ field_key: "is_active_on_wa", operator: "eq", value: true })] }]);
    const operators = screen.getByLabelText("Condition");
    expect(within(operators).getByRole("option", { name: "is" })).toBeInTheDocument();
    expect(within(operators).queryByRole("option", { name: "contains" })).not.toBeInTheDocument();
  });

  it("resets the value when the operator's shape changes", () => {
    const onChange = renderBuilder([{ index: 0, rules: [ruleFixture()] }]);
    fireEvent.change(screen.getByLabelText("Condition"), { target: { value: "exists" } });
    // "Priya" is not a boolean; carrying it over would send a value the compiler rejects.
    expect(onChange).toHaveBeenCalledWith([
      { index: 0, rules: [expect.objectContaining({ operator: "exists", value: true })] },
    ]);
  });

  it("keeps the value when the shape survives the operator change", () => {
    const onChange = renderBuilder([{ index: 0, rules: [ruleFixture()] }]);
    fireEvent.change(screen.getByLabelText("Condition"), { target: { value: "starts" } });
    expect(onChange).toHaveBeenCalledWith([
      { index: 0, rules: [expect.objectContaining({ operator: "starts", value: "Priya" })] },
    ]);
  });

  it("rebuilds the rule when the source changes, since nothing carries across", () => {
    const onChange = renderBuilder([{ index: 0, rules: [ruleFixture()] }]);
    fireEvent.change(screen.getByLabelText("Source"), { target: { value: "tag" } });
    expect(onChange).toHaveBeenCalledWith([
      { index: 0, rules: [expect.objectContaining({ field_source: "tag", operator: "has_tag" })] },
    ]);
  });

  it("offers a tag picker rather than free text for a tag rule", () => {
    renderBuilder([
      { index: 0, rules: [ruleFixture({ field_source: "tag", field_key: "tags", operator: "has_tag", value: "" })] },
    ]);
    const value = screen.getByLabelText("Value");
    expect(within(value).getByRole("option", { name: "vip" })).toBeInTheDocument();
  });

  it("offers an enum attribute's own values", () => {
    renderBuilder([
      { index: 0, rules: [ruleFixture({ field_source: "attribute", field_key: "plan", operator: "eq", value: "" })] },
    ]);
    const value = screen.getByLabelText("Value");
    expect(within(value).getByRole("option", { name: "premium" })).toBeInTheDocument();
  });

  it("draws two inputs for a between range", () => {
    renderBuilder([
      { index: 0, rules: [ruleFixture({ field_key: "created_at", operator: "between", value: ["", ""] })] },
    ]);
    expect(screen.getByLabelText("From")).toBeInTheDocument();
    expect(screen.getByLabelText("To")).toBeInTheDocument();
  });

  it("drops a group once its last condition is removed", () => {
    const onChange = renderBuilder([{ index: 0, rules: [ruleFixture()] }]);
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("warns when there are no conditions at all", () => {
    renderBuilder([]);
    expect(screen.getByText(/matches every contact/)).toBeInTheDocument();
  });
});

// --- Editor -------------------------------------------------------------------------------------------------------

describe("SegmentEditor", () => {
  it("posts the whole rule set on create", async () => {
    seedCatalogs();
    responses["/api/v1/segments"] = segmentFixture({ id: "new" });
    withProviders(<SegmentEditor />);

    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "New segment" } });
    fireEvent.click(screen.getByRole("button", { name: "Create segment" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toMatchObject({ name: "New segment", match_type: "all", rules: [] });
  });

  it("blocks a save when a rule is incomplete, and says which", async () => {
    seedCatalogs();
    withProviders(<SegmentEditor segment={segmentFixture({ rules: [ruleFixture({ value: "" })] })} />);

    fireEvent.click(await screen.findByRole("button", { name: "Save segment" }));
    expect(screen.getByText("Enter a value")).toBeInTheDocument();
    expect(writes).toHaveLength(0);
  });

  it("warns before saving that changed conditions clear the cached size", async () => {
    seedCatalogs();
    withProviders(<SegmentEditor segment={segmentFixture()} />);

    fireEvent.change(await screen.findByLabelText("Condition"), { target: { value: "eq" } });
    expect(screen.getByText(/clears this segment's saved size/)).toBeInTheDocument();
  });

  it("warns that an empty rule set matches everyone", async () => {
    seedCatalogs();
    withProviders(<SegmentEditor segment={segmentFixture({ rules: [] })} />);
    // Said in three places by design: the builder, the summary and the pre-save warning.
    expect((await screen.findAllByText(/matches every contact/)).length).toBeGreaterThan(0);
  });

  it("surfaces a server rejection verbatim", async () => {
    seedCatalogs();
    withProviders(<SegmentEditor />);

    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "Duplicate" } });
    fireEvent.click(screen.getByRole("button", { name: "Create segment" }));

    expect(await screen.findByText("network disabled under test")).toBeInTheDocument();
  });

  it("opens prefilled from a seed while still creating", async () => {
    seedCatalogs();
    responses["/api/v1/segments"] = segmentFixture({ id: "copy" });
    withProviders(
      <SegmentEditor initial={segmentFixture({ name: "Lapsed customers (copy)" })} />,
    );

    expect(await screen.findByLabelText("Name")).toHaveValue("Lapsed customers (copy)");
    fireEvent.click(screen.getByRole("button", { name: "Create segment" }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/segments");
  });
});

// --- Actions ------------------------------------------------------------------------------------------------------

describe("SegmentActions", () => {
  it("offers refresh to a reader, because the endpoint is gated on read", () => {
    permissions.value = ["segments:read"];
    withProviders(<SegmentActions segment={segmentFixture()} />);
    expect(screen.getByRole("button", { name: "Refresh count" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("calls the action Evaluate when nothing has been computed yet", () => {
    withProviders(
      <SegmentActions segment={segmentFixture({ cached_count: null, last_evaluated_at: null })} />,
    );
    expect(screen.getByRole("button", { name: "Evaluate" })).toBeInTheDocument();
  });

  it("warns that nothing checks whether a segment is in use before deleting it", () => {
    withProviders(<SegmentActions segment={segmentFixture()} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(
      within(screen.getByRole("dialog")).getByText(/does not check whether anything uses/),
    ).toBeInTheDocument();
  });

  it("hides every write control from a reader", () => {
    permissions.value = ["segments:read"];
    withProviders(<SegmentActions segment={segmentFixture()} />);
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Duplicate" })).not.toBeInTheDocument();
  });
});

// --- List ---------------------------------------------------------------------------------------------------------

describe("SegmentList", () => {
  it("lists segments with their size and conditions", async () => {
    responses["/api/v1/segments"] = [segmentFixture()];
    withProviders(<SegmentList />);

    expect(await screen.findByRole("link", { name: "Lapsed customers" })).toHaveAttribute(
      "href",
      "/segments/s1",
    );
    // Counts are grouped by the shared formatter.
    expect(screen.getAllByText("1,240 contacts").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1 condition").length).toBeGreaterThan(0);
  });

  it("filters by state without a round trip", async () => {
    responses["/api/v1/segments"] = [
      segmentFixture({ id: "a", name: "Evaluated one" }),
      segmentFixture({ id: "b", name: "Fresh one", cached_count: null, last_evaluated_at: null }),
    ];
    withProviders(<SegmentList />);

    await screen.findByRole("link", { name: "Evaluated one" });
    fireEvent.change(screen.getByLabelText("State"), { target: { value: "stale" } });

    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Evaluated one" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Fresh one" })).toBeInTheDocument();
  });

  it("invites a writer to create the first segment", async () => {
    responses["/api/v1/segments"] = [];
    withProviders(<SegmentList />);
    expect(await screen.findByText("No segments yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New segment" })).toBeInTheDocument();
  });

  it("hides the create control from a reader", async () => {
    permissions.value = ["segments:read"];
    responses["/api/v1/segments"] = [];
    withProviders(<SegmentList />);
    await screen.findByText("No segments yet");
    expect(screen.queryByRole("link", { name: "New segment" })).not.toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<SegmentList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("reflows to stacked cards below md, keeping every fact the table carries", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("max-width"),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    responses["/api/v1/segments"] = [segmentFixture()];
    withProviders(<SegmentList />);

    await screen.findByRole("link", { name: "Lapsed customers" });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem").length).toBeGreaterThan(0);
    expect(screen.getByText("1,240 contacts")).toBeInTheDocument();
    expect(screen.getByText("1 condition")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

// --- Detail --------------------------------------------------------------------------------------------------------

describe("SegmentDetail", () => {
  function seed(segment: Segment, contacts: unknown[] = [], total = contacts.length) {
    responses[`/api/v1/segments/{segment_id}`] = segment;
    responses[`/api/v1/segments/{segment_id}/contacts`] = {
      data: contacts,
      page: { limit: 50, has_more: false, total },
    };
    seedCatalogs();
  }

  it("shows the conditions and the live membership", async () => {
    seed(segmentFixture(), [
      {
        id: "c1",
        type: "contact",
        full_name: "Priya S.",
        phone_e164: "+911111111111",
        opt_in_status: "opted_in",
        last_contacted_at: null,
      },
    ]);
    withProviders(<SegmentDetail segmentId="s1" />);

    expect(await screen.findByText("1 contact match right now")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Priya S." })).toBeInTheDocument();
  });

  it("explains that an un-evaluated segment has no saved size but a live list", async () => {
    seed(segmentFixture({ cached_count: null, last_evaluated_at: null }), []);
    withProviders(<SegmentDetail segmentId="s1" />);
    expect(await screen.findByText(/no saved size/)).toBeInTheDocument();
  });

  it("says the cached number is not what a campaign sends to", async () => {
    seed(segmentFixture(), []);
    withProviders(<SegmentDetail segmentId="s1" />);
    expect(await screen.findByText(/resolve the segment live at dispatch/)).toBeInTheDocument();
  });

  it("says when more contacts match than are shown", async () => {
    seed(segmentFixture(), [
      { id: "c1", type: "contact", full_name: "A", phone_e164: "+91", opt_in_status: "unknown", last_contacted_at: null },
    ], 900);
    withProviders(<SegmentDetail segmentId="s1" />);
    expect(await screen.findByText(/900 contacts match; the first 1 are shown/)).toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<SegmentDetail segmentId="s1" />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

// --- Navigation -----------------------------------------------------------------------------------------------------

describe("navigation — segments entry", () => {
  it("is visible to someone holding segments:read", () => {
    expect(visibleNavItems((code) => code === "segments:read").map((item) => item.path)).toContain(
      "/segments",
    );
  });

  it("is hidden from someone without it", () => {
    expect(visibleNavItems((code) => code === "inbox:read").map((item) => item.path)).not.toContain(
      "/segments",
    );
  });
});
