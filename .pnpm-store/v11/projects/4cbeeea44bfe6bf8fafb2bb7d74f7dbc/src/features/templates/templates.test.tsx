import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ButtonDraft, TemplateDraft } from "@/features/templates/components";
import {
  analyzeTemplate,
  analyzeVariables,
  blankDraft,
  cloneDraft,
  componentOf,
  draftFromTemplate,
  mediaHeaderFormat,
  templateButtons,
  toComponents,
} from "@/features/templates/components";
import {
  availableLanguages,
  filterTemplates,
  PAGE_SIZE,
  registryCounts,
  selectTemplatePage,
  sortTemplates,
} from "@/features/templates/selectors";
import { TemplateActions } from "@/features/templates/TemplateActions";
import { QualityChip, TemplateStatusChip } from "@/features/templates/TemplateBadges";
import { TemplateBubble } from "@/features/templates/TemplateBubble";
import { TemplateFilters } from "@/features/templates/TemplateFilters";
import { TemplateTable } from "@/features/templates/TemplateTable";
import { toCreateRequest, toUpdateRequest, validateDraft } from "@/features/templates/templateForm";
import type { Template, TemplateListQuery } from "@/features/templates/types";
import { DEFAULT_LIST_QUERY } from "@/features/templates/types";
import { VariableInspector } from "@/features/templates/VariableInspector";
import { formatAge, formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

// Permission-gated actions read the session; the roster is swapped per test.
const permissions = { value: ["templates:read", "templates:write", "templates:sync"] };
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

function templateFixture(overrides: Partial<Template> = {}): Template {
  return {
    id: "t1",
    type: "template",
    waba_id: "w1",
    name: "order_update",
    language: "en_US",
    category: "utility",
    status: "approved",
    quality_score: "green",
    rejection_reason: null,
    components: [
      { type: "header", format: "text", text: "Order {{1}}" },
      { type: "body", text: "Hi {{1}}, your order {{2}} ships today. Thanks {{1}}!" },
      { type: "footer", text: "Reply STOP to opt out" },
      {
        type: "buttons",
        buttons: [
          { type: "url", text: "Track order", url: "https://example.com" },
          { type: "quick_reply", text: "Not me" },
        ],
      },
    ],
    variable_count: 3,
    has_media_header: false,
    is_sendable: true,
    last_synced_at: "2026-07-22T09:00:00Z",
    row_version: 4,
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-21T10:00:00Z",
    ...overrides,
  };
}

function query(overrides: Partial<TemplateListQuery> = {}): TemplateListQuery {
  return { ...DEFAULT_LIST_QUERY, ...overrides };
}

function draftFixture(overrides: Partial<TemplateDraft> = {}): TemplateDraft {
  return {
    ...blankDraft(),
    waba_id: "w1",
    name: "order_update",
    language: "en_US",
    body_text: "Hi {{1}}",
    ...overrides,
  };
}

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

beforeEach(() => {
  permissions.value = ["templates:read", "templates:write", "templates:sync"];
});

describe("selectors — filtering, sorting, pagination", () => {
  const rows = [
    templateFixture({ id: "a", name: "alpha_promo", status: "draft", category: "marketing", language: "en_US", created_at: "2026-07-01T00:00:00Z" }),
    templateFixture({ id: "b", name: "bravo_alert", status: "approved", category: "utility", language: "hi_IN", created_at: "2026-07-02T00:00:00Z" }),
    templateFixture({ id: "c", name: "charlie_otp", status: "approved", category: "authentication", language: "en_US", created_at: "2026-07-03T00:00:00Z" }),
  ];

  it("normalises separators so a spaced search finds a snake_case name", () => {
    // Template names are lower-snake by Meta's rules; an operator does not type them that way.
    expect(filterTemplates(rows, query({ q: "alpha promo" })).map((row) => row.id)).toEqual(["a"]);
    expect(filterTemplates(rows, query({ q: "BRAVO-ALERT" })).map((row) => row.id)).toEqual(["b"]);
    expect(filterTemplates(rows, query({ q: "  " }))).toHaveLength(3);
  });

  it("filters by status, category and language independently", () => {
    expect(filterTemplates(rows, query({ status: "approved" })).map((r) => r.id)).toEqual(["b", "c"]);
    expect(filterTemplates(rows, query({ category: "marketing" })).map((r) => r.id)).toEqual(["a"]);
    expect(filterTemplates(rows, query({ language: "en_US" })).map((r) => r.id)).toEqual(["a", "c"]);
  });

  it("combines filters conjunctively", () => {
    const matched = filterTemplates(rows, query({ status: "approved", language: "en_US" }));
    expect(matched.map((row) => row.id)).toEqual(["c"]);
  });

  it("sorts without mutating the input", () => {
    const before = rows.map((row) => row.id);
    expect(sortTemplates(rows, "-created_at").map((r) => r.id)).toEqual(["c", "b", "a"]);
    expect(sortTemplates(rows, "name").map((r) => r.id)).toEqual(["a", "b", "c"]);
    expect(sortTemplates(rows, "-name").map((r) => r.id)).toEqual(["c", "b", "a"]);
    expect(rows.map((row) => row.id)).toEqual(before);
  });

  it("reports page counts over the filtered set and clamps a dead page", () => {
    const filtered = selectTemplatePage(rows, query({ status: "approved" }));
    expect(filtered.total).toBe(2);
    expect(selectTemplatePage(rows, query({ page: 9 })).page).toBe(1);
  });

  it("slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 3 }, (_, index) =>
      templateFixture({ id: `t${index}`, name: `tpl_${index}` }),
    );
    expect(selectTemplatePage(many, query()).rows).toHaveLength(PAGE_SIZE);
    expect(selectTemplatePage(many, query({ page: 2 })).rows).toHaveLength(3);
  });

  it("offers only the languages the registry actually holds", () => {
    expect(availableLanguages(rows)).toEqual(["en_US", "hi_IN"]);
  });

  it("counts what can actually be broadcast", () => {
    const counts = registryCounts([
      templateFixture({ status: "approved", is_sendable: true }),
      templateFixture({ status: "pending", is_sendable: false }),
      templateFixture({ status: "rejected", is_sendable: false }),
    ]);
    expect(counts).toMatchObject({ total: 3, approved: 1, pending: 1, rejected: 1, sendable: 1 });
  });
});

describe("components — reading a definition", () => {
  it("finds components case-insensitively, because Meta upper-cases them", () => {
    const upper = templateFixture({
      components: [{ type: "BODY", text: "Hello" }],
    });
    expect(componentOf(upper.components, "body")?.text).toBe("Hello");
  });

  it("reads a stored template back into an editable draft", () => {
    const draft = draftFromTemplate(templateFixture());
    expect(draft).toMatchObject({
      name: "order_update",
      language: "en_US",
      category: "utility",
      header_format: "text",
      header_text: "Order {{1}}",
      footer_text: "Reply STOP to opt out",
    });
    expect(draft.buttons).toHaveLength(2);
    expect(draft.buttons[0]).toMatchObject({ type: "url", url: "https://example.com" });
  });

  it("names a clone distinctly while keeping the definition", () => {
    const draft = cloneDraft(templateFixture());
    expect(draft.name).toBe("order_update_copy");
    expect(draft.body_text).toContain("your order");
  });

  it("reports a media header's kind and that it has no text", () => {
    const media = templateFixture({
      components: [{ type: "header", format: "image" }, { type: "body", text: "Hi" }],
      has_media_header: true,
    });
    expect(mediaHeaderFormat(media)).toBe("image");
    expect(draftFromTemplate(media).header_text).toBe("");
    // A media header carries no text, so it can declare no variables.
    expect(analyzeTemplate(media).header).toEqual([]);
  });

  it("returns no media format for a text header", () => {
    expect(mediaHeaderFormat(templateFixture())).toBeNull();
  });

  it("tolerates an unexpected stored shape", () => {
    const odd = templateFixture({ components: [], category: "nonsense" });
    const draft = draftFromTemplate(odd);
    expect(draft.header_format).toBe("none");
    expect(draft.category).toBe("marketing");
    expect(templateButtons(odd)).toEqual([]);
  });
});

describe("components — writing the wire shape", () => {
  it("emits only the components the definition uses", () => {
    const components = toComponents(draftFixture({ footer_text: "  " }));
    expect(components.map((component) => component.type)).toEqual(["body"]);
  });

  it("gives a media header no text, because Meta rejects the combination", () => {
    const components = toComponents(
      draftFixture({ header_format: "image", header_text: "leftover" }),
    );
    const header = components.find((component) => component.type === "header");
    expect(header).toEqual({ type: "header", format: "image" });
    expect(header).not.toHaveProperty("text");
  });

  it("keeps a text header's text", () => {
    const components = toComponents(
      draftFixture({ header_format: "text", header_text: "Order {{1}}" }),
    );
    expect(components.find((c) => c.type === "header")).toEqual({
      type: "header",
      format: "text",
      text: "Order {{1}}",
    });
  });

  it("sends only the target field a button type uses", () => {
    const buttons: ButtonDraft[] = [
      { type: "url", text: "Visit", url: "https://example.com", phone_number: "+911" },
      { type: "quick_reply", text: "No thanks", url: "x", phone_number: "y" },
    ];
    const emitted = toComponents(draftFixture({ buttons })).find((c) => c.type === "buttons");
    const list = emitted?.buttons as Record<string, unknown>[];
    expect(list[0]).toEqual({ type: "url", text: "Visit", url: "https://example.com" });
    // A quick reply carries no target; sending a stale url would describe a button it is not.
    expect(list[1]).toEqual({ type: "quick_reply", text: "No thanks" });
  });
});

describe("components — variable analysis", () => {
  it("counts distinct variables and their occurrences", () => {
    const analysis = analyzeVariables("Order {{1}}", "Hi {{1}}, order {{2}} ships. Thanks {{1}}!");
    expect(analysis.total).toBe(3);
    expect(analysis.body).toEqual([
      { index: 1, component: "body", occurrences: 2 },
      { index: 2, component: "body", occurrences: 1 },
    ]);
    expect(analysis.problems).toEqual([]);
  });

  it("reports a numbering gap, which Meta rejects outright", () => {
    const analysis = analyzeVariables("", "Hi {{1}}, ref {{3}}");
    expect(analysis.problems[0]).toMatch(/numbered from \{\{1\}\} with no gaps/);
  });

  it("reports a header carrying more than one variable", () => {
    const analysis = analyzeVariables("{{1}} and {{2}}", "Body");
    expect(analysis.problems.some((p) => p.includes("at most 1 variable"))).toBe(true);
  });

  it("has nothing to report for a template without variables", () => {
    expect(analyzeVariables("", "No variables here").total).toBe(0);
  });
});

describe("templateForm — validation", () => {
  it("requires the identity fields only when creating", () => {
    const empty = { ...blankDraft(), body_text: "Hi" };
    expect(validateDraft(empty, { creating: true })).toMatchObject({
      waba_id: expect.any(String),
      name: expect.any(String),
    });
    expect(validateDraft(empty, { creating: false }).name).toBeUndefined();
  });

  it("enforces Meta's template name rule", () => {
    expect(validateDraft(draftFixture({ name: "Order Update" }), { creating: true }).name).toMatch(
      /lower-case letters, digits and underscores/,
    );
    expect(validateDraft(draftFixture({ name: "order_update_2" }), { creating: true }).name).toBeUndefined();
  });

  it("requires body text and bounds every component", () => {
    expect(validateDraft(draftFixture({ body_text: "   " }), { creating: true }).body_text).toMatch(
      /needs text/,
    );
    expect(
      validateDraft(draftFixture({ body_text: "x".repeat(1025) }), { creating: true }).body_text,
    ).toMatch(/1024 characters/);
    expect(
      validateDraft(draftFixture({ footer_text: "x".repeat(61) }), { creating: true }).footer_text,
    ).toMatch(/60 characters/);
    expect(
      validateDraft(draftFixture({ header_format: "text", header_text: "x".repeat(61) }), {
        creating: true,
      }).header_text,
    ).toMatch(/60 characters/);
  });

  it("refuses a footer with variables", () => {
    expect(
      validateDraft(draftFixture({ footer_text: "Hi {{1}}" }), { creating: true }).footer_text,
    ).toMatch(/cannot contain variables/);
  });

  it("requires a text header to have text, but not a media header", () => {
    expect(
      validateDraft(draftFixture({ header_format: "text", header_text: "" }), { creating: true })
        .header_text,
    ).toMatch(/needs text/);
    expect(
      validateDraft(draftFixture({ header_format: "image" }), { creating: true }).header_text,
    ).toBeUndefined();
  });

  it("surfaces a placeholder gap against the component that has it", () => {
    const errors = validateDraft(draftFixture({ body_text: "Hi {{2}}" }), { creating: true });
    expect(errors.body_text).toMatch(/no gaps/);
  });

  it("requires each button's label and its own target field", () => {
    const label = validateDraft(
      draftFixture({ buttons: [{ type: "quick_reply", text: "", url: "", phone_number: "" }] }),
      { creating: true },
    );
    expect(label.buttons).toMatch(/needs a label/);

    const url = validateDraft(
      draftFixture({ buttons: [{ type: "url", text: "Go", url: "", phone_number: "" }] }),
      { creating: true },
    );
    expect(url.buttons).toMatch(/needs a URL/);

    const phone = validateDraft(
      draftFixture({ buttons: [{ type: "phone_number", text: "Call", url: "", phone_number: "" }] }),
      { creating: true },
    );
    expect(phone.buttons).toMatch(/needs a phone number/);
  });

  it("accepts a well-formed definition", () => {
    expect(validateDraft(draftFixture(), { creating: true })).toEqual({});
  });
});

describe("templateForm — requests", () => {
  it("carries the submit flag, which is what separates a draft from a Meta round trip", () => {
    expect(toCreateRequest(draftFixture(), false).submit).toBe(false);
    expect(toCreateRequest(draftFixture(), true).submit).toBe(true);
  });

  it("omits identity from an update, because the contract does not accept it", () => {
    const template = templateFixture({ row_version: 9 });
    const body = toUpdateRequest(draftFromTemplate(template), template, false);
    expect(body.row_version).toBe(9);
    expect(body).not.toHaveProperty("name");
    expect(body).not.toHaveProperty("language");
    expect(body).not.toHaveProperty("waba_id");
  });
});

describe("lib/format", () => {
  it("renders unknown values as a dash rather than zero or a blank", () => {
    expect(formatCount(null)).toBe(UNKNOWN);
    expect(formatDateTime(null)).toBe(UNKNOWN);
    expect(formatDateTime("not-a-date")).toBe(UNKNOWN);
  });

  it("says 'never' when there is no timestamp at all", () => {
    expect(formatAge(null)).toBe("never");
    expect(formatAge(new Date(Date.now() - 5000).toISOString())).toBe("just now");
    expect(formatAge(new Date(Date.now() - 7200_000).toISOString())).toBe("2 h ago");
  });
});

describe("TemplateStatusChip / QualityChip", () => {
  it("labels known statuses and passes unknown ones through verbatim", () => {
    withProviders(
      <>
        <TemplateStatusChip value="pending" />
        <TemplateStatusChip value="some_new_state" />
      </>,
    );
    expect(screen.getByText("Pending review")).toBeInTheDocument();
    expect(screen.getByText("some_new_state")).toBeInTheDocument();
  });

  it("says a missing quality rating is 'not rated', not bad", () => {
    withProviders(<QualityChip value={null} />);
    expect(screen.getByText("Not rated")).toBeInTheDocument();
  });
});

describe("TemplateBubble", () => {
  it("renders the message with its footer and buttons", () => {
    withProviders(
      <TemplateBubble
        header="Order {{1}}"
        body="Hi {{1}}"
        footer="Reply STOP"
        mediaFormat={null}
        buttons={[{ type: "url", text: "Track order", url: "https://x", phone_number: "" }]}
      />,
    );
    expect(screen.getByText("Order {{1}}")).toBeInTheDocument();
    expect(screen.getByText("Reply STOP")).toBeInTheDocument();
    expect(screen.getByText("Track order")).toBeInTheDocument();
  });

  it("shows a media header as a placeholder supplied per send", () => {
    withProviders(
      <TemplateBubble header="" body="Hi" footer="" mediaFormat="image" buttons={[]} />,
    );
    expect(screen.getByText("Image header")).toBeInTheDocument();
    expect(screen.getByText("Supplied per send")).toBeInTheDocument();
  });

  it("says so when there is no body yet", () => {
    withProviders(<TemplateBubble header="" body="" footer="" mediaFormat={null} buttons={[]} />);
    expect(screen.getByText("No body text yet.")).toBeInTheDocument();
  });
});

describe("VariableInspector", () => {
  it("lists each variable with its component and occurrence count", () => {
    withProviders(<VariableInspector analysis={analyzeTemplate(templateFixture())} />);
    expect(screen.getByText("{{2}}")).toBeInTheDocument();
    expect(screen.getByText(/must supply 3 values/)).toBeInTheDocument();
  });

  it("raises numbering problems as an alert", () => {
    withProviders(<VariableInspector analysis={analyzeVariables("", "Hi {{2}}")} />);
    expect(within(screen.getByRole("alert")).getByText(/no gaps/)).toBeInTheDocument();
  });

  it("explains a media header separately when there are no variables", () => {
    withProviders(<VariableInspector analysis={analyzeVariables("", "Hello")} mediaHeader />);
    expect(screen.getByText(/file is supplied per send/)).toBeInTheDocument();
  });
});

describe("TemplateTable", () => {
  it("renders a template with its status and a link to its detail page", () => {
    withProviders(<TemplateTable templates={[templateFixture()]} />);
    expect(screen.getByRole("link", { name: "order_update" })).toHaveAttribute(
      "href",
      "/templates/t1",
    );
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("surfaces the rejection reason where the operator will look for it", () => {
    withProviders(
      <TemplateTable
        templates={[
          templateFixture({ status: "rejected", rejection_reason: "Body violates policy 4.2" }),
        ]}
      />,
    );
    expect(screen.getByText("Body violates policy 4.2")).toBeInTheDocument();
  });
});

describe("TemplateFilters", () => {
  it("returns to the first page whenever a filter changes", () => {
    const onChange = vi.fn();
    withProviders(
      <TemplateFilters filters={query({ page: 4 })} languages={["en_US"]} onChange={onChange} />,
    );
    fireEvent.change(screen.getByLabelText("Approval status"), { target: { value: "approved" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: "approved", page: 1 }));
  });

  it("offers only the languages present in the registry", () => {
    withProviders(
      <TemplateFilters filters={query()} languages={["en_US", "hi_IN"]} onChange={vi.fn()} />,
    );
    const select = screen.getByLabelText("Language");
    expect(within(select).getByRole("option", { name: "hi_IN" })).toBeInTheDocument();
    expect(within(select).queryByRole("option", { name: "fr_FR" })).not.toBeInTheDocument();
  });
});

describe("TemplateActions — permission and status gating", () => {
  it("offers clone but not edit once Meta owns the template", () => {
    withProviders(<TemplateActions template={templateFixture({ status: "approved" })} />);
    expect(screen.getByRole("button", { name: "Clone" })).toBeInTheDocument();
    // An edit would be overwritten by the next sync, so it is not offered at all.
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("offers edit for a draft and for a rejected template", () => {
    withProviders(<TemplateActions template={templateFixture({ status: "draft" })} />);
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();

    withProviders(<TemplateActions template={templateFixture({ id: "t2", status: "rejected" })} />);
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(2);
  });

  it("hides every control a read-only user cannot use", () => {
    permissions.value = ["templates:read"];
    withProviders(<TemplateActions template={templateFixture({ status: "draft" })} />);
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clone" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});

describe("TemplateActions — delete confirmation", () => {
  it("warns that a submitted template is withdrawn from Meta", () => {
    withProviders(<TemplateActions template={templateFixture({ status: "approved" })} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(within(screen.getByRole("dialog")).getByText(/withdrawn from Meta/)).toBeInTheDocument();
  });

  it("says a never-submitted draft is only removed locally", () => {
    withProviders(<TemplateActions template={templateFixture({ status: "draft" })} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(
      within(screen.getByRole("dialog")).getByText(/never been submitted/),
    ).toBeInTheDocument();
  });
});
