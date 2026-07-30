import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignActions } from "@/features/campaigns/CampaignActions";
import { CampaignProgressBar, CampaignStatusChip } from "@/features/campaigns/CampaignBadges";
import { CampaignFilters } from "@/features/campaigns/CampaignFilters";
import { CampaignTable } from "@/features/campaigns/CampaignTable";
import { CampaignTimeline } from "@/features/campaigns/CampaignTimeline";
import { CampaignWizardProgress } from "@/features/campaigns/CampaignWizardProgress";
import {
  campaignToForm,
  duplicateToForm,
  followUpToForm,
  toCreateRequest,
  toUpdateRequest,
} from "@/features/campaigns/campaignForm";
import { formatCount, formatMoney, formatRate, UNKNOWN } from "@/features/campaigns/format";
import {
  blankSchedule,
  parseSteps,
  toScheduleRequest,
  validateSchedule,
} from "@/features/campaigns/scheduleForm";
import {
  completionRatio,
  deliveryStats,
  filterCampaigns,
  PAGE_SIZE,
  rate,
  selectCampaignPage,
  sortCampaigns,
} from "@/features/campaigns/selectors";
import { placeholderIndices, templateShape } from "@/features/campaigns/templateShape";
import type { Campaign, CampaignListQuery, Template } from "@/features/campaigns/types";
import { DEFAULT_LIST_QUERY } from "@/features/campaigns/types";

// Permission-gated actions read the session; the roster is swapped per test.
const permissions = {
  value: ["campaigns:read", "campaigns:write", "campaigns:send", "campaigns:manage"],
};
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

function campaignFixture(overrides: Partial<Campaign> = {}): Campaign {
  return {
    id: "c1",
    type: "campaign",
    name: "Reactivation July",
    phone_number_id: "pn1",
    template_id: "t1",
    status: "draft",
    audience_type: "segment",
    audience_ref: { segment_id: "s1" },
    variable_map: { header: [], body: [] },
    total_recipients: 100,
    queued_count: 0,
    sent_count: 0,
    delivered_count: 0,
    read_count: 0,
    failed_count: 0,
    replied_count: 0,
    row_version: 3,
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function query(overrides: Partial<CampaignListQuery> = {}): CampaignListQuery {
  return { ...DEFAULT_LIST_QUERY, ...overrides };
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
  permissions.value = [
    "campaigns:read",
    "campaigns:write",
    "campaigns:send",
    "campaigns:manage",
  ];
});

describe("selectors — filtering, sorting, pagination", () => {
  const rows = [
    campaignFixture({ id: "a", name: "Alpha", status: "draft", created_at: "2026-07-01T00:00:00Z", total_recipients: 10 }),
    campaignFixture({ id: "b", name: "Bravo", status: "running", created_at: "2026-07-02T00:00:00Z", total_recipients: 50 }),
    campaignFixture({ id: "c", name: "Charlie", status: "draft", created_at: "2026-07-03T00:00:00Z", total_recipients: 30 }),
  ];

  it("matches search case-insensitively on the name", () => {
    expect(filterCampaigns(rows, query({ q: "brav" })).map((row) => row.id)).toEqual(["b"]);
    expect(filterCampaigns(rows, query({ q: "  " })).length).toBe(3);
  });

  it("filters by exact status", () => {
    expect(filterCampaigns(rows, query({ status: "draft" })).map((row) => row.id)).toEqual([
      "a",
      "c",
    ]);
  });

  it("sorts by each supported key without mutating the input", () => {
    const before = rows.map((row) => row.id);
    expect(sortCampaigns(rows, "-created_at").map((row) => row.id)).toEqual(["c", "b", "a"]);
    expect(sortCampaigns(rows, "created_at").map((row) => row.id)).toEqual(["a", "b", "c"]);
    expect(sortCampaigns(rows, "-name").map((row) => row.id)).toEqual(["c", "b", "a"]);
    expect(sortCampaigns(rows, "-total_recipients").map((row) => row.id)).toEqual(["b", "c", "a"]);
    expect(rows.map((row) => row.id)).toEqual(before);
  });

  it("reports page counts over the filtered set, not the whole list", () => {
    const page = selectCampaignPage(rows, query({ status: "draft" }));
    expect(page.total).toBe(2);
    expect(page.totalPages).toBe(1);
    expect(page.rows.map((row) => row.id)).toEqual(["c", "a"]);
  });

  it("clamps a page number past the end, so a narrowing filter cannot strand the user", () => {
    const page = selectCampaignPage(rows, query({ page: 9 }));
    expect(page.page).toBe(1);
    expect(page.rows).toHaveLength(3);
  });

  it("slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 5 }, (_, index) =>
      campaignFixture({ id: `c${index}`, created_at: `2026-07-${String(index + 1).padStart(2, "0")}T00:00:00Z` }),
    );
    const first = selectCampaignPage(many, query());
    const second = selectCampaignPage(many, query({ page: 2 }));
    expect(first.rows).toHaveLength(PAGE_SIZE);
    expect(second.rows).toHaveLength(5);
    expect(second.totalPages).toBe(2);
  });
});

describe("selectors — delivery statistics", () => {
  it("returns null rather than zero when there is nothing to divide by", () => {
    expect(rate(0, 0)).toBeNull();
    expect(rate(1, 0)).toBeNull();
    expect(rate(1, 4)).toBe(0.25);
  });

  it("measures each rate against its own funnel stage", () => {
    const stats = deliveryStats(
      campaignFixture({
        total_recipients: 200,
        sent_count: 100,
        delivered_count: 80,
        read_count: 40,
        failed_count: 20,
        replied_count: 8,
      }),
    );
    // Delivery is of sent, not of the whole roster — a campaign still fanning out is not "failing".
    expect(stats.deliveryRate).toBeCloseTo(0.8);
    expect(stats.readRate).toBeCloseTo(0.5);
    expect(stats.failureRate).toBeCloseTo(0.1);
    expect(stats.replyRate).toBeCloseTo(0.1);
  });

  it("counts sent and failed as handled, and has no ratio for an empty roster", () => {
    expect(completionRatio(campaignFixture({ total_recipients: 0 }))).toBeNull();
    expect(
      completionRatio(campaignFixture({ total_recipients: 100, sent_count: 60, failed_count: 20 })),
    ).toBeCloseTo(0.8);
  });
});

describe("format", () => {
  it("renders unknown values as a dash rather than zero", () => {
    expect(formatCount(null)).toBe(UNKNOWN);
    expect(formatRate(null)).toBe(UNKNOWN);
    expect(formatMoney(null)).toBe(UNKNOWN);
    expect(formatRate(0.1234)).toBe("12.3%");
  });

  it("keeps money at the scale the server sent it, never parsing it into a float", () => {
    // The trailing zeros carry the rate card's scale; a float round-trip would discard them.
    expect(formatMoney("1234.5000")).toBe("1,234.5000");
    expect(formatMoney("0.0085", "INR")).toBe("0.0085 INR");
    expect(formatMoney("-12.50")).toBe("-12.50");
    expect(formatMoney("1000000")).toBe("1,000,000");
  });
});

describe("templateShape", () => {
  function template(overrides: Partial<Template> = {}): Template {
    return {
      id: "t1",
      type: "template",
      waba_id: "w1",
      name: "reactivation",
      language: "en",
      category: "MARKETING",
      status: "APPROVED",
      quality_score: null,
      rejection_reason: null,
      components: [
        { type: "HEADER", format: "TEXT", text: "Hello {{1}}" },
        { type: "BODY", text: "Hi {{1}}, your plan {{2}} is ready. {{1}}" },
        { type: "FOOTER", text: "Reply STOP to opt out" },
      ],
      variable_count: 3,
      has_media_header: false,
      is_sendable: true,
      last_synced_at: null,
      row_version: 0,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
      ...overrides,
    };
  }

  it("counts each placeholder once, in order", () => {
    expect(placeholderIndices("Hi {{2}} and {{1}} and {{1}}")).toEqual([1, 2]);
    expect(placeholderIndices(undefined)).toEqual([]);
  });

  it("counts header and body variables separately", () => {
    const shape = templateShape(template());
    expect(shape.headerCount).toBe(1);
    expect(shape.bodyCount).toBe(2);
    expect(shape.footerText).toBe("Reply STOP to opt out");
  });

  it("treats a media header as carrying no variables", () => {
    const shape = templateShape(
      template({ components: [{ type: "HEADER", format: "IMAGE" }, { type: "BODY", text: "Hi" }] }),
    );
    expect(shape.headerCount).toBe(0);
    expect(shape.mediaHeaderFormat).toBe("IMAGE");
  });

  it("has an empty shape when no template is chosen", () => {
    expect(templateShape(undefined).bodyCount).toBe(0);
  });
});

describe("campaignForm", () => {
  it("reads an existing campaign back into form values", () => {
    const values = campaignToForm(
      campaignFixture({
        audience_type: "tag",
        audience_ref: { tag_ids: ["tag1", "tag2"] },
        variable_map: { body: [{ source: "field", key: "first_name", fallback: "there" }] },
      }),
    );
    expect(values.audience_type).toBe("tag");
    expect(values.tag_ids).toEqual(["tag1", "tag2"]);
    expect(values.body[0]).toEqual({
      source: "field",
      key: "first_name",
      value: "",
      fallback: "there",
    });
  });

  it("falls back safely when the stored shape is unexpected", () => {
    const values = campaignToForm(
      campaignFixture({ audience_type: "upload", audience_ref: null, variable_map: null }),
    );
    // `upload` is not offered — the server refuses it — so the form opens on a type it can build.
    expect(values.audience_type).toBe("segment");
    expect(values.tag_ids).toEqual([]);
    expect(values.body).toEqual([]);
  });

  it("names a duplicate distinctly while keeping the definition", () => {
    const values = duplicateToForm(campaignFixture());
    expect(values.name).toBe("Reactivation July (copy)");
    expect(values.segment_id).toBe("s1");
  });

  it("names a governed follow-up distinctly while keeping the source audience", () => {
    const values = followUpToForm(campaignFixture({ audience_ref: { segment_id: "warm" } }));
    expect(values.name).toBe("Reactivation July — follow-up");
    expect(values.segment_id).toBe("warm");
  });

  it("sends only the audience keys the chosen type uses", () => {
    const base = campaignToForm(campaignFixture());
    const asTag = toCreateRequest({ ...base, audience_type: "tag", tag_ids: ["t9"] });
    // A stale segment_id must not travel with a tag audience.
    expect(asTag.audience_ref).toEqual({ tag_ids: ["t9"] });
    expect(toCreateRequest(base).audience_ref).toEqual({ segment_id: "s1" });
  });

  it("splits key and value by source, and drops an empty fallback", () => {
    const base = campaignToForm(campaignFixture());
    const body = toCreateRequest({
      ...base,
      body: [
        { source: "literal", key: "ignored", value: "Hello", fallback: "" },
        { source: "attribute", key: "plan", value: "", fallback: "basic" },
      ],
    }).variable_map?.body;

    expect(body?.[0]).toEqual({ source: "literal", key: null, value: "Hello", fallback: null });
    expect(body?.[1]).toEqual({ source: "attribute", key: "plan", value: null, fallback: "basic" });
  });

  it("carries row_version on an update so a concurrent edit conflicts instead of overwriting", () => {
    const campaign = campaignFixture({ row_version: 7 });
    expect(toUpdateRequest(campaignToForm(campaign), campaign.row_version).row_version).toBe(7);
  });
});

describe("CampaignWizardProgress", () => {
  const steps = [
    { key: "audience", label: "Audience" },
    { key: "template", label: "Template" },
    { key: "preview", label: "Preview" },
    { key: "schedule", label: "Schedule" },
    { key: "approval", label: "Approval" },
    { key: "confirmation", label: "Confirmation" },
  ];

  it("shows the complete governed journey without a separate scrolling tab strip", () => {
    render(
      <CampaignWizardProgress
        steps={steps}
        currentIndex={0}
        includeAnalytics
        onSelect={vi.fn()}
      />,
    );

    const navigation = screen.getByRole("navigation", { name: "Wizard steps" });
    expect(within(navigation).getByText("Audience")).toBeInTheDocument();
    expect(within(navigation).getByText("Confirmation")).toBeInTheDocument();
    expect(within(navigation).getByText("Analytics")).toBeInTheDocument();
    expect(navigation).not.toHaveClass("overflow-x-auto");
  });

  it("marks the current step and only lets operators revisit completed steps", () => {
    const onSelect = vi.fn();
    render(<CampaignWizardProgress steps={steps} currentIndex={2} onSelect={onSelect} />);

    const current = screen.getByRole("button", { name: /preview/i });
    expect(current).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("button", { name: /schedule/i })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /audience/i }));
    expect(onSelect).toHaveBeenCalledWith(0);
  });
});

describe("scheduleForm", () => {
  it("requires a future time for a one-time send", () => {
    const draft = blankSchedule();
    expect(validateSchedule(draft)).toMatch(/needs a date and time/);
    expect(validateSchedule({ ...draft, run_at: "2020-01-01T10:00" })).toMatch(/in the future/);
    const future = new Date(Date.now() + 86_400_000).toISOString().slice(0, 16);
    expect(validateSchedule({ ...draft, run_at: future })).toBeNull();
  });

  it("requires five cron fields and a sane window", () => {
    const draft = { ...blankSchedule(), schedule_type: "recurring" as const };
    expect(validateSchedule({ ...draft, cron_expr: "0 10 *" })).toMatch(/5 fields/);
    expect(validateSchedule(draft)).toBeNull();
    expect(
      validateSchedule({ ...draft, starts_on: "2026-08-10", ends_on: "2026-08-01" }),
    ).toMatch(/cannot precede/);
  });

  it("rejects drip sequences that are empty, negative or repeated", () => {
    const draft = {
      ...blankSchedule(),
      schedule_type: "drip" as const,
      starts_at: "2026-08-01T10:00",
    };
    expect(validateSchedule({ ...draft, steps: "" })).toMatch(/at least one step/);
    expect(validateSchedule({ ...draft, steps: "0, -5" })).toMatch(/cannot be negative/);
    expect(validateSchedule({ ...draft, steps: "0, 0" })).toMatch(/must be distinct/);
    expect(validateSchedule(draft)).toBeNull();
  });

  it("parses step offsets and ignores blanks", () => {
    expect(parseSteps(" 0, 1440 , , 4320 ")).toEqual([0, 1440, 4320]);
  });

  it("sends only the fields the chosen shape uses", () => {
    const recurring = toScheduleRequest({
      ...blankSchedule(),
      schedule_type: "recurring",
      cron_expr: "0 10 * * *",
      starts_on: "",
      ends_on: "",
    });
    expect(recurring).toMatchObject({ schedule_type: "recurring", cron_expr: "0 10 * * *" });
    expect(recurring).not.toHaveProperty("run_at");
    expect(recurring.starts_on).toBeNull();

    const drip = toScheduleRequest({
      ...blankSchedule(),
      schedule_type: "drip",
      starts_at: "2026-08-01T10:00",
      steps: "0, 60",
    });
    expect(drip.steps).toEqual([0, 60]);
    expect(drip).not.toHaveProperty("cron_expr");
  });
});

describe("CampaignTable", () => {
  it("renders a campaign with its status, audience and a link to its detail page", () => {
    withProviders(<CampaignTable campaigns={[campaignFixture()]} />);

    expect(screen.getByRole("link", { name: "Reactivation July" })).toHaveAttribute(
      "href",
      "/campaigns/c1",
    );
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getAllByText("Segment").length).toBeGreaterThan(0);
  });

  it("shows progress against the roster", () => {
    withProviders(
      <CampaignTable
        campaigns={[
          campaignFixture({ status: "running", total_recipients: 100, sent_count: 25 }),
        ]}
      />,
    );
    expect(screen.getByText("25 of 100 (25.0%)")).toBeInTheDocument();
  });
});

describe("CampaignProgressBar", () => {
  it("says an empty roster has no recipients rather than showing 0%", () => {
    withProviders(<CampaignProgressBar campaign={campaignFixture({ total_recipients: 0 })} />);
    expect(screen.getByText("No recipients")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  });
});

describe("CampaignStatusChip", () => {
  it("labels known statuses and passes unknown ones through verbatim", () => {
    withProviders(
      <>
        <CampaignStatusChip value="running" />
        <CampaignStatusChip value="some_new_state" />
      </>,
    );
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("some_new_state")).toBeInTheDocument();
  });
});

describe("CampaignFilters", () => {
  it("returns to the first page whenever a filter changes", () => {
    const onChange = vi.fn();
    withProviders(<CampaignFilters filters={query({ page: 4 })} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "running" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: "running", page: 1 }));
  });

  it("offers every known status", () => {
    withProviders(<CampaignFilters filters={query()} onChange={vi.fn()} />);
    const select = screen.getByLabelText("Status");
    expect(within(select).getByRole("option", { name: "Cancelled" })).toBeInTheDocument();
  });
});

describe("CampaignActions — permission gating", () => {
  it("offers the write, send and manage actions a running campaign allows", () => {
    withProviders(
      <CampaignActions campaign={campaignFixture({ status: "running", failed_count: 2 })} />,
    );

    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry 2 failed/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    // A running campaign is past the point where editing or deleting is allowed.
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("hides every control a read-only user cannot use", () => {
    permissions.value = ["campaigns:read"];
    withProviders(<CampaignActions campaign={campaignFixture({ status: "running", failed_count: 2 })} />);

    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Retry/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Duplicate" })).not.toBeInTheDocument();
  });

  it("offers send but not lifecycle control to a sender without manage", () => {
    permissions.value = ["campaigns:read", "campaigns:send"];
    withProviders(<CampaignActions campaign={campaignFixture({ status: "running" })} />);

    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("turns duplication into a clear follow-up action after results are final", () => {
    withProviders(<CampaignActions campaign={campaignFixture({ status: "completed" })} />);
    expect(screen.getByRole("button", { name: "Create follow-up" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Duplicate" })).not.toBeInTheDocument();
  });

  it("gates a draft on send permission before it can be dispatched", () => {
    permissions.value = ["campaigns:read", "campaigns:write"];
    withProviders(<CampaignActions campaign={campaignFixture({ status: "draft" })} />);

    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send now" })).not.toBeInTheDocument();
  });
});

describe("CampaignActions — confirmation", () => {
  it("warns that sent messages cannot be unsent before dispatching", () => {
    withProviders(<CampaignActions campaign={campaignFixture({ status: "draft" })} />);

    fireEvent.click(screen.getByRole("button", { name: "Send now" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/cannot be unsent/)).toBeInTheDocument();
    expect(within(dialog).getByText(/100 recipients/)).toBeInTheDocument();
  });

  it("confirms a delete before destroying the draft", () => {
    withProviders(<CampaignActions campaign={campaignFixture({ status: "draft" })} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(
      within(screen.getByRole("dialog")).getByText(/Reactivation July/),
    ).toBeInTheDocument();
  });
});

describe("CampaignTimeline", () => {
  it("marks the stages a draft has not reached yet", () => {
    withProviders(<CampaignTimeline campaign={campaignFixture()} progress={undefined} />);

    expect(screen.getByText("Draft created")).toBeInTheDocument();
    expect(screen.getByText("Not dispatched yet")).toBeInTheDocument();
    expect(screen.getByText("Not finished yet")).toBeInTheDocument();
  });

  it("reports batch progress once the campaign is running", () => {
    withProviders(
      <CampaignTimeline
        campaign={campaignFixture({ status: "running", sent_count: 40 })}
        progress={{
          status: "running",
          total: 100,
          pending: 60,
          queued: 0,
          sent: 40,
          delivered: 30,
          read: 10,
          failed: 0,
          batches_total: 4,
          batches_done: 2,
        }}
      />,
    );
    expect(screen.getByText("2 of 4 batches complete")).toBeInTheDocument();
    expect(screen.getByText("40 of 100 handled")).toBeInTheDocument();
  });

  it("shows a paused campaign as stopped rather than finished", () => {
    withProviders(
      <CampaignTimeline campaign={campaignFixture({ status: "paused" })} progress={undefined} />,
    );
    expect(screen.getByText("Paused")).toBeInTheDocument();
    expect(screen.getByText("Not finished yet")).toBeInTheDocument();
  });
});
