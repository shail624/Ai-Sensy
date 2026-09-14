import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BulkActionsBar } from "@/features/contacts/BulkActionsBar";

// Permission-gated surfaces read the session; the roster is swapped per test.
const permissions = {
  value: ["contacts:read", "contacts:write", "contacts:export", "campaigns:write"],
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

const posts: { path: string; body: unknown }[] = [];
const patches: { path: string; body: unknown }[] = [];
const navigations: { to: string; state: unknown }[] = [];

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => (to: string, options?: { state?: unknown }) => {
      navigations.push({ to, state: options?.state });
    },
  };
});

function campaignFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "cam1",
    type: "campaign",
    name: "Reactivation blast",
    status: "draft",
    audience_type: "list",
    audience_ref: { contact_ids: ["c9"] },
    row_version: 3,
    ...overrides,
  };
}
const progress = {
  value: {
    id: "b1",
    type: "bulk",
    operation: "bulk_update",
    action: "add_tags",
    job_status: "running",
    status: "running",
    summary: { total: 2, processed: 1, succeeded: 1, failed: 0, skipped: 0 },
    errors: [] as { id: string | null; code: string; message: string }[],
    error_report_url: null as string | null,
    created_at: "2026-07-24T00:00:00Z",
    completed_at: null as string | null,
  },
};

const GETS: Record<string, unknown> = {
  "/api/v1/tags": [
    {
      id: "t1",
      type: "tag",
      name: "VIP",
      color: "#5b53e8",
      description: null,
      usage_count: 2,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    },
  ],
  "/api/v1/campaigns": {
    data: [campaignFixture(), campaignFixture({ id: "cam2", name: "Already sent", status: "sent" })],
    page: { limit: 50, has_more: false, total: 2 },
  },
  "/api/v1/custom-attributes": [
    {
      id: "a1",
      type: "custom_attribute",
      key_name: "reactivation_status",
      label: "Reactivation status",
      data_type: "enum",
      enum_values: ["pending", "won"],
      is_indexed: true,
      is_pii: false,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    },
  ],
};

vi.mock("@/lib/api/client", () => {
  const GET = async (path: string) => {
    if (path === "/api/v1/contacts/bulk/{bulk_id}") return { data: progress.value };
    return path in GETS ? { data: GETS[path] } : { error: new Error(`no stub for ${path}`) };
  };
  const POST = async (path: string, init: { body: unknown }) => {
    posts.push({ path, body: init.body });
    return { data: { job: { id: "b1", type: "bulk", status: "queued", poll_url: "/x" } } };
  };
  const PATCH = async (path: string, init: { body: unknown }) => {
    patches.push({ path, body: init.body });
    return { data: campaignFixture({ row_version: 4 }) };
  };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET, POST, PATCH, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

const RULES = [{ field: "opt_in_status", op: "eq", value: "opted_in" }];

/** Scope queries to the dialog — the bar behind it carries buttons with the same labels. */
function dialog() {
  return within(screen.getByRole("dialog"));
}

function renderBar(selected = ["c1", "c2"], onClear = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <BulkActionsBar
          selectedIds={new Set(selected)}
          onClear={onClear}
          rules={RULES as never}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return onClear;
}

beforeEach(() => {
  posts.length = 0;
  patches.length = 0;
  navigations.length = 0;
  permissions.value = ["contacts:read", "contacts:write", "contacts:export", "campaigns:write"];
  progress.value = { ...progress.value, job_status: "running", errors: [], error_report_url: null };
});

describe("BulkActionsBar", () => {
  it("stays out of the way until something is selected", () => {
    renderBar([]);
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument();
  });

  it("shows the count and every permitted action", () => {
    renderBar();
    expect(screen.getByText("2 selected")).toBeInTheDocument();
    for (const label of ["Tag", "Untag", "Attribute", "Campaign", "Export", "Delete", "Clear"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("hides the actions the caller has no permission for", () => {
    permissions.value = ["contacts:read"];
    renderBar();
    expect(screen.getByText("2 selected")).toBeInTheDocument();
    for (const label of ["Tag", "Untag", "Attribute", "Campaign", "Export", "Delete"]) {
      expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
  });

  it("sends the selection and the §30 count guard when tagging", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Tag" }));

    const apply = await screen.findByRole("button", { name: "Apply" });
    expect(apply).toBeDisabled(); // nothing chosen yet

    fireEvent.click(await dialog().findByRole("checkbox", { name: /VIP/ }));
    fireEvent.click(dialog().getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({
      path: "/api/v1/contacts/bulk-update",
      body: {
        ids: ["c1", "c2"],
        expected_count: 2,
        action: "add_tags",
        payload: { tags: ["t1"] },
      },
    });
  });

  it("sends an attribute edit as the API's payload shape", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Attribute" }));

    await dialog().findByRole("option", { name: "Reactivation status" }); // definitions loaded
    fireEvent.change(dialog().getByLabelText("Attribute"), {
      target: { value: "reactivation_status" },
    });
    fireEvent.change(dialog().getByLabelText("Value"), { target: { value: "won" } });
    fireEvent.click(dialog().getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]?.body).toEqual({
      ids: ["c1", "c2"],
      expected_count: 2,
      action: "set_attributes",
      payload: { attributes: { reactivation_status: "won" } },
    });
  });

  it("confirms before deleting and posts to bulk-delete", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByText(/cannot be undone/i)).toBeInTheDocument();
    fireEvent.click(dialog().getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({
      path: "/api/v1/contacts/bulk-delete",
      body: { ids: ["c1", "c2"], expected_count: 2 },
    });
  });

  it("exports the filtered view by rule, never by selection", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Export" }));

    expect(await screen.findByText(/the whole filtered view/i)).toBeInTheDocument();
    fireEvent.change(dialog().getByLabelText("Format"), { target: { value: "xlsx" } });
    fireEvent.click(dialog().getByRole("button", { name: "Export" }));

    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({
      path: "/api/v1/contacts/export",
      body: { format: "xlsx", match_type: "all", rules: RULES },
    });
  });

  it("offers only draft campaigns and merges the selection into the audience", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Campaign" }));

    await dialog().findByRole("option", { name: "Reactivation blast" });
    expect(dialog().queryByRole("option", { name: "Already sent" })).not.toBeInTheDocument();

    fireEvent.change(dialog().getByLabelText("Draft campaign"), { target: { value: "cam1" } });
    fireEvent.click(dialog().getByRole("button", { name: "Apply" }));

    await waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0]).toEqual({
      path: "/api/v1/campaigns/{campaign_id}",
      body: {
        audience_type: "list",
        audience_ref: { contact_ids: ["c9", "c1", "c2"] },
        row_version: 3,
      },
    });
    expect(await screen.findByText(/added to Reactivation blast/)).toBeInTheDocument();
  });

  it("hands the selection to the campaign wizard instead of rebuilding it", async () => {
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Campaign" }));
    fireEvent.click(
      await dialog().findByRole("button", { name: /start a new campaign from these contacts/i }),
    );
    expect(navigations).toEqual([
      { to: "/campaigns/new", state: { contactIds: ["c1", "c2"] } },
    ]);
  });

  it("reports partial success with its per-item errors", async () => {
    progress.value = {
      ...progress.value,
      job_status: "partial_success",
      status: "partial_success",
      summary: { total: 2, processed: 2, succeeded: 1, failed: 1, skipped: 0 },
      errors: [{ id: "c2", code: "conflict", message: "row_version is stale" }],
      error_report_url: "/api/v1/jobs/b1/errors.csv",
    };
    renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Tag" }));
    fireEvent.click(await dialog().findByRole("checkbox", { name: /VIP/ }));
    fireEvent.click(dialog().getByRole("button", { name: "Apply" }));

    expect(await screen.findByText("Finished with errors")).toBeInTheDocument();
    expect(screen.getByText(/1 updated · 1 failed/)).toBeInTheDocument();
    expect(screen.getByText(/row_version is stale/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download error report" })).toHaveAttribute(
      "href",
      "/api/v1/jobs/b1/errors.csv",
    );
  });

  it("clears the selection once a finished job is dismissed", async () => {
    progress.value = { ...progress.value, job_status: "succeeded", status: "succeeded" };
    const onClear = renderBar();
    fireEvent.click(screen.getByRole("button", { name: "Tag" }));
    fireEvent.click(await dialog().findByRole("checkbox", { name: /VIP/ }));
    fireEvent.click(dialog().getByRole("button", { name: "Apply" }));

    fireEvent.click(await screen.findByRole("button", { name: "Done" }));
    expect(onClear).toHaveBeenCalled();
  });
});
