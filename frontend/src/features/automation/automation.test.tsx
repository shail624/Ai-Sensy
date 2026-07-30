import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AutomationWorkspace } from "@/features/automation/AutomationWorkspace";
import type { AutomationFlow, AutomationRun, AutomationVersion } from "@/features/automation/types";

const { permissions, get, post, patch } = vi.hoisted(() => ({
  permissions: { value: ["automations:read", "automations:write", "automations:publish"] },
  get: vi.fn(), post: vi.fn(), patch: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ useHasPermission: (code: string) => permissions.value.includes(code) }));
vi.mock("@/lib/api/client", () => ({
  api: { GET: get, POST: post, PATCH: patch, DELETE: vi.fn() },
  authClient: { POST: vi.fn() }, setSessionExpiredHandler: vi.fn(), refreshOnce: vi.fn(),
}));

let current: AutomationFlow;
let versions: AutomationVersion[];
let runs: AutomationRun[];

function fixture(overrides: Partial<AutomationFlow> = {}): AutomationFlow {
  return {
    id: "a1", name: "Lead welcome", description: "Welcome new contacts", status: "draft",
    graph: { nodes: [], edges: [] }, active_version_no: null, has_unpublished_changes: true,
    row_version: 0, created_at: "2026-07-30T10:00:00Z", updated_at: "2026-07-30T10:00:00Z",
    created_by: "u1", updated_by: "u1", ...overrides,
  };
}

function renderWorkspace(path = "/automation?flow=a1") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><AutomationWorkspace /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  permissions.value = ["automations:read", "automations:write", "automations:publish"];
  current = fixture(); versions = []; runs = [];
  get.mockReset(); post.mockReset(); patch.mockReset();
  get.mockImplementation(async (path: string) => {
    if (path.endsWith("/versions")) return { data: { data: versions } };
    if (path.endsWith("/runs")) return { data: { data: runs } };
    if (path.startsWith("/api/v1/automation-runs/")) return { data: runs[0] };
    if (path === "/api/v1/automations") return { data: { data: [current], total: 1 } };
    if (path.includes("/automations/")) return { data: current };
    return { error: new Error("unexpected GET") };
  });
  patch.mockImplementation(async (_path: string, options: { body: Partial<AutomationFlow> & { graph?: AutomationFlow["graph"] } }) => {
    current = { ...current, ...options.body, row_version: current.row_version + 1, has_unpublished_changes: true, updated_at: "2026-07-30T11:00:00Z" };
    return { data: current };
  });
  post.mockImplementation(async (path: string, options?: { body?: { name?: string } }) => {
    if (path.endsWith("/validate")) return { data: { valid: true, issues: [] } };
    if (path.endsWith("/publish")) {
      current = { ...current, status: "published", active_version_no: 1, has_unpublished_changes: false, row_version: current.row_version + 1 };
      return { data: current };
    }
    if (path === "/api/v1/automations") {
      current = fixture({ id: "a2", name: options?.body?.name ?? "New automation" });
      return { data: current };
    }
    if (path.endsWith("/test-runs")) {
      const run: AutomationRun = {
        id: "run-1", automation_id: current.id, version_no: 1, mode: "test", status: "queued",
        correlation_id: "correlation-1", total_steps: 2, completed_steps: 0,
        created_by: "Priya", created_at: "2026-07-30T12:00:00Z", started_at: null,
        finished_at: null, error_code: null, error_detail: null, attempts: [],
      };
      runs = [run];
      return { data: run };
    }
    return { data: current };
  });
});

describe("versioned automation authoring", () => {
  it("creates a durable draft from a simple workspace", async () => {
    renderWorkspace("/automation");
    expect(await screen.findByText("Lead welcome")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New automation" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Renewal reminder" } });
    fireEvent.click(screen.getByRole("button", { name: "Create draft" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/v1/automations", expect.objectContaining({ body: expect.objectContaining({ name: "Renewal reminder" }) })));
  });

  it("saves a typed sequence and publishes only after server validation", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    expect(await screen.findByText("Draft saved safely.", { exact: true })).toBeVisible();
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "notification"]);
    expect(body.graph.edges).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("button", { name: "Publish" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(post.mock.calls.map((call) => call[0])).toContain("/api/v1/automations/{automation_id}/publish"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run test" })).toBeEnabled());
  });

  it("queues a safe test run with explicit JSON and shows durable history", async () => {
    current = fixture({ status: "published", active_version_no: 1, has_unpublished_changes: false });
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Run test" }));
    expect(screen.getByRole("dialog", { name: "Test automation" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Test data (JSON)"), {
      target: { value: '{"contact":{"tier":"gold"}}' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run safe test" }));
    await waitFor(() => expect(post.mock.calls.map((call) => call[0])).toContain("/api/v1/automations/{automation_id}/test-runs"));
    expect(await screen.findByText("Test run queued safely. Every action will be simulated.")).toBeVisible();
    expect(await screen.findByText("0/2 steps", { exact: false })).toBeVisible();
  });

  it("shows fail-closed publication issues without calling publish", async () => {
    current = fixture({ graph: { nodes: [{ id: "c1", kind: "campaign", config: { campaign_id: "00000000-0000-0000-0000-000000000000" } }], edges: [] } });
    post.mockImplementation(async (path: string) => path.endsWith("/validate") ? { data: { valid: false, issues: [{ code: "campaign_approval_required", message: "Connect every campaign proposal to a downstream human approval.", node_id: "c1" }] } } : { data: current });
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(await screen.findByText("Publication checks need attention")).toBeInTheDocument();
    expect(screen.getByText("• Connect every campaign proposal to a downstream human approval.")).toBeInTheDocument();
    expect(post.mock.calls.some((call) => String(call[0]).endsWith("/publish"))).toBe(false);
  });

  it("keeps readers read-only and execution unavailable", async () => {
    permissions.value = ["automations:read"];
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    expect(screen.queryByRole("button", { name: "New automation" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trigger" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run test" })).toBeDisabled();
  });
});
