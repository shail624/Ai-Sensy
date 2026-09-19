import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AutomationWorkspace } from "@/features/automation/AutomationWorkspace";
import type { AutomationFlow, AutomationRun, AutomationTriggerReceipt, AutomationVersion } from "@/features/automation/types";

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
let receipts: AutomationTriggerReceipt[];

function fixture(overrides: Partial<AutomationFlow> = {}): AutomationFlow {
  return {
    id: "a1", name: "Lead welcome", description: "Welcome new contacts", status: "draft",
    graph: { nodes: [], edges: [] }, active_version_no: null, next_run_at: null, has_unpublished_changes: true,
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
  current = fixture(); versions = []; runs = []; receipts = [];
  get.mockReset(); post.mockReset(); patch.mockReset();
  get.mockImplementation(async (path: string) => {
    if (path === "/api/v1/tags") return { data: [{ id: "tag-1", name: "VIP", color: "#0f766e", description: null, usage_count: 0, created_at: "2026-07-30T10:00:00Z", updated_at: "2026-07-30T10:00:00Z" }] };
    if (path === "/api/v1/users") return { data: { data: [{ id: "11111111-1111-4111-8111-111111111111", email: "agent@vi.co", full_name: "Priya Agent", phone: null, avatar_url: null, timezone: "Asia/Kolkata", locale: "en", is_active: true, is_superuser: false, mfa_enabled: false, roles: ["Agent"], row_version: 0, created_at: "2026-07-30T10:00:00Z", updated_at: "2026-07-30T10:00:00Z" }], page: { limit: 50, has_more: false, next_cursor: null, total: 1 } } };
    if (path.endsWith("/versions")) return { data: { data: versions } };
    if (path.endsWith("/runs")) return { data: { data: runs } };
    if (path.endsWith("/trigger-receipts")) return { data: { data: receipts } };
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
      current = { ...current, status: "published", active_version_no: 1, next_run_at: null, has_unpublished_changes: false, row_version: current.row_version + 1 };
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
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "A new inbound customer needs attention" },
    });
    expect(screen.getByText("Live contract")).toBeVisible();
    expect(screen.getByText(/existing Notification Center/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    expect(await screen.findByText("Draft saved safely.", { exact: true })).toBeVisible();
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "notification"]);
    expect(body.graph.nodes[1].config).toEqual({
      message: "A new inbound customer needs attention",
    });
    expect(body.graph.edges).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("button", { name: "Publish" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(post.mock.calls.map((call) => call[0])).toContain("/api/v1/automations/{automation_id}/publish"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run test" })).toBeEnabled());
  });

  it("authors the governed Human handoff node without changing safe test mode", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Human handoff" }));
    fireEvent.change(screen.getByLabelText("Handoff reason"), {
      target: { value: "Customer asked for an account specialist" },
    });
    expect(screen.getByText("Live contract")).toBeVisible();
    expect(screen.getByText(/Message received can run all six proven internal effects/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "handoff"]);
    expect(body.graph.nodes[1].config).toEqual({
      reason: "Customer asked for an account specialist",
    });
    expect(screen.getByText("Safe test mode uses the immutable version and records every step. Actions are simulated; no business record or customer message can change.")).toBeVisible();
  });

  it("authors a privacy-safe live condition before task creation", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    expect(screen.getByDisplayValue("payload.message_type")).toBeVisible();
    expect(screen.getByText(/Live event decisions support the suggested metadata fields/)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "image" } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    fireEvent.change(screen.getByLabelText("Task title"), { target: { value: "Call inbound customer" } });
    fireEvent.change(screen.getByLabelText("Task type"), { target: { value: "call" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "high" } });
    fireEvent.change(screen.getByLabelText("Due in minutes"), { target: { value: "90" } });
    expect(screen.getByText(/assigned to the active automation publisher/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "condition", "action"]);
    expect(body.graph.nodes[1].config).toEqual({
      field: "payload.message_type",
      operator: "eq",
      value: "image",
    });
    expect(body.graph.nodes[2].config).toEqual({
      action: "create_task",
      title: "Call inbound customer",
      task_type: "call",
      priority: "high",
      due_in_minutes: 90,
    });
    expect(body.graph.edges).toHaveLength(2);
  });

  it("authors a bounded terminal Yes/No branch with explicit edge evidence", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    expect(screen.getByRole("button", { name: "Enable Yes/No branch" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), { target: { value: "message.received" } });
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "text" } });
    expect(screen.getByText(/Build Trigger, Condition, one Yes action and one No action/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "Yes branch selected" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "No branch selected" },
    });
    const enableBranch = screen.getByRole("button", { name: "Enable Yes/No branch" });
    expect(enableBranch).toBeEnabled();
    fireEvent.click(enableBranch);
    expect(screen.getByText("Yes branch")).toBeVisible();
    expect(screen.getByText("No branch")).toBeVisible();
    expect(screen.getByText(/Each side runs in order with up to two distinct effects/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Use linear gate" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "notification",
      "notification",
    ]);
    expect(body.graph.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: body.graph.nodes[1].id, target: body.graph.nodes[2].id, label: "yes" }),
      expect.objectContaining({ source: body.graph.nodes[1].id, target: body.graph.nodes[3].id, label: "no" }),
    ]));
  });

  it("authors a second ordered effect on both bounded branches", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), { target: { value: "message.received" } });
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Enable Yes/No branch" }));

    fireEvent.click(screen.getByRole("button", { name: "Add Create task to Yes branch" }));
    expect(screen.getByText("Yes step 2")).toBeVisible();
    expect(screen.getByRole("button", { name: "Add Create task to Yes branch" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Add Create task to No branch" }));
    expect(screen.getByText("No step 2")).toBeVisible();
    expect(screen.getByText(/Arbitrary merges, branch-specific Delay\/Wait, nested branches and external actions fail safely/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "notification",
      "action",
      "notification",
      "action",
    ]);
    expect(body.graph.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: body.graph.nodes[1].id, target: body.graph.nodes[2].id, label: "yes" }),
      expect.objectContaining({ source: body.graph.nodes[2].id, target: body.graph.nodes[3].id }),
      expect.objectContaining({ source: body.graph.nodes[1].id, target: body.graph.nodes[4].id, label: "no" }),
      expect.objectContaining({ source: body.graph.nodes[4].id, target: body.graph.nodes[5].id }),
    ]));
  });

  it("authors one shared follow-up after either bounded branch outcome", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), { target: { value: "message.received" } });
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Enable Yes/No branch" }));

    const addShared = screen.getByRole("button", { name: "Add Create task after both branches" });
    expect(addShared).toBeEnabled();
    fireEvent.click(addShared);
    expect(screen.getByText("After both")).toBeVisible();
    expect(screen.getByText(/One optional shared follow-up runs after either outcome/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Add Create task after both branches" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    const [, condition, yesNode, noNode, sharedNode] = body.graph.nodes;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "notification",
      "notification",
      "action",
    ]);
    expect(body.graph.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: condition.id, target: yesNode.id, label: "yes" }),
      expect.objectContaining({ source: condition.id, target: noNode.id, label: "no" }),
      expect.objectContaining({ source: yesNode.id, target: sharedNode.id }),
      expect.objectContaining({ source: noNode.id, target: sharedNode.id }),
    ]));
  });

  it("authors one durable shared delay before the common follow-up", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), { target: { value: "message.received" } });
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Enable Yes/No branch" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Create task after both branches" }));

    const addDelay = screen.getByRole("button", { name: "Add shared delay before follow-up" });
    expect(addDelay).toBeEnabled();
    fireEvent.click(addDelay);
    expect(screen.getByText("Shared delay")).toBeVisible();
    expect(screen.getByText("After both")).toBeVisible();
    expect(screen.getByLabelText("Delay (seconds)")).toHaveValue(3600);
    expect(screen.getByText(/may have one durable Delay immediately before it/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Add shared delay before follow-up" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    const [, condition, yesNode, noNode, delayNode, sharedNode] = body.graph.nodes;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "notification",
      "notification",
      "delay",
      "action",
    ]);
    expect(body.graph.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: condition.id, target: yesNode.id, label: "yes" }),
      expect.objectContaining({ source: condition.id, target: noNode.id, label: "no" }),
      expect.objectContaining({ source: yesNode.id, target: delayNode.id }),
      expect.objectContaining({ source: noNode.id, target: delayNode.id }),
      expect.objectContaining({ source: delayNode.id, target: sharedNode.id }),
    ]));

    fireEvent.click(screen.getByRole("button", { name: "Remove step" }));
    expect(screen.queryByText("Shared delay")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalledTimes(2));
    const withoutDelay = patch.mock.calls[1]![1].body;
    const [, , restoredYes, restoredNo, restoredShared] = withoutDelay.graph.nodes;
    expect(withoutDelay.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "notification",
      "notification",
      "action",
    ]);
    expect(withoutDelay.graph.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: restoredYes.id, target: restoredShared.id }),
      expect.objectContaining({ source: restoredNo.id, target: restoredShared.id }),
    ]));
  });

  it("authors a connected multi-effect live sequence", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    expect(screen.getByText(/Arbitrary merges, branch-specific Delay\/Wait, nested branches and external actions fail safely/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "tag",
      "action",
      "notification",
    ]);
    expect(body.graph.edges).toHaveLength(3);
  });

  it("authors an event-safe Contact created live sequence", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    expect(screen.getByLabelText("Event")).toHaveValue("contact.created");
    expect(screen.getByText(/Contact created supports tag changes and internal Notification/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "A new contact entered the workspace" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "tag",
      "notification",
    ]);
    expect(body.graph.nodes[0].config).toEqual({ event: "contact.created" });
    expect(body.graph.edges).toHaveLength(2);
  });

  it("authors an event-safe Conversation auto-resolved follow-up sequence", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), {
      target: { value: "conversation.auto_resolved" },
    });
    expect(screen.getByText(/Conversation auto-resolved and Lead stage changed support/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.change(screen.getByDisplayValue("payload.message_type"), {
      target: { value: "payload.previous_status" },
    });
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "open" } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Follow up after auto-resolution" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "An inactive conversation was auto-resolved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "action",
      "tag",
      "notification",
    ]);
    expect(body.graph.nodes[0].config).toEqual({ event: "conversation.auto_resolved" });
    expect(body.graph.nodes[1].config).toEqual({
      field: "payload.previous_status",
      operator: "eq",
      value: "open",
    });
    expect(body.graph.edges).toHaveLength(4);
  });

  it("authors a live Lead stage changed follow-up with stage-safe metadata", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), {
      target: { value: "lead.stage_changed" },
    });
    expect(screen.getByText(/Lead stage changed support safe internal follow-up Tasks/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Condition" }));
    fireEvent.change(screen.getByDisplayValue("payload.message_type"), {
      target: { value: "payload.to_stage" },
    });
    fireEvent.change(screen.getByLabelText("Value"), {
      target: { value: "lead_confirmed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Follow up confirmed lead" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "A lead moved to confirmed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "condition",
      "action",
      "notification",
    ]);
    expect(body.graph.nodes[0].config).toEqual({ event: "lead.stage_changed" });
    expect(body.graph.nodes[1].config).toEqual({
      field: "payload.to_stage",
      operator: "eq",
      value: "lead_confirmed",
    });
    expect(body.graph.edges).toHaveLength(3);
  });

  it("authors a timezone-backed live Schedule notification and shows its next run", async () => {
    current = fixture({
      status: "published",
      active_version_no: 1,
      next_run_at: "2026-08-24T03:30:00Z",
      has_unpublished_changes: false,
    });
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    expect(screen.getByText(/Next scheduled live run/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.change(screen.getByLabelText("Event"), { target: { value: "schedule" } });
    expect(screen.getByLabelText("Five-field cron schedule")).toHaveValue("0 9 * * 1-5");
    expect(screen.getByText(/Runs in the organization timezone/)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Five-field cron schedule"), {
      target: { value: "30 9 * * 1-5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Delay" }));
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "Review scheduled follow-ups" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "delay",
      "notification",
    ]);
    expect(body.graph.nodes[0].config).toEqual({
      event: "schedule",
      schedule_cron: "30 9 * * 1-5",
    });
    expect(body.graph.edges).toHaveLength(2);
  });

  it("authors one durable live delay inside a connected sequence", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    fireEvent.click(screen.getByRole("button", { name: "Delay" }));
    fireEvent.change(screen.getByLabelText("Delay (seconds)"), { target: { value: "900" } });
    expect(screen.getByText(/Completed steps stay checkpointed/)).toBeVisible();
    expect(screen.getAllByText("Live contract")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "action",
      "delay",
      "notification",
    ]);
    expect(body.graph.nodes[2].config).toEqual({ seconds: 900 });
    expect(body.graph.edges).toHaveLength(3);
  });

  it("authors one bounded same-customer live Wait before an internal effect", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Wait for event" }));
    expect(screen.getByLabelText("Resume event")).toHaveValue("message.received");
    expect(screen.getByLabelText("Timeout (seconds)")).toHaveValue(86400);
    expect(screen.getByText(/same customer's future Message received/)).toBeVisible();
    expect(screen.getAllByText("Live contract")).toHaveLength(1);
    fireEvent.change(screen.getByLabelText("Timeout (seconds)"), {
      target: { value: "900" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.change(screen.getByLabelText("Internal message"), {
      target: { value: "The new contact replied" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual([
      "trigger",
      "wait",
      "notification",
    ]);
    expect(body.graph.nodes[1].config).toEqual({
      event: "message.received",
      timeout_seconds: 900,
    });
    expect(body.graph.edges).toHaveLength(2);
  });

  it("authors a same-customer live Task completed Wait", async () => {
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Wait for event" }));
    fireEvent.change(screen.getByLabelText("Resume event"), {
      target: { value: "task.completed" },
    });
    expect(screen.getByText(/future Message received, Task completed or Lead stage changed fact/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Notification" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes[1].config).toEqual({
      event: "task.completed",
      timeout_seconds: 86400,
    });
  });

  it("authors a live Apply tag action from the existing CRM tag picker", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));
    expect(screen.getByText("Live contract")).toBeVisible();
    expect(screen.getByLabelText("Tag")).toHaveValue("tag-1");
    expect(screen.getByText(/already-present tag completes safely/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "tag"]);
    expect(body.graph.nodes[1].config).toEqual({ tag_id: "tag-1" });
    expect(body.graph.edges).toHaveLength(1);
  });

  it("authors a live Remove tag action from the existing CRM tag picker", async () => {
    permissions.value.push("contacts:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/tags")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove tag" }));
    expect(screen.getByText("Live contract")).toBeVisible();
    expect(screen.getByLabelText("Tag")).toHaveValue("tag-1");
    expect(screen.getByText(/already-absent tag completes safely/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "remove_tag"]);
    expect(body.graph.nodes[1].config).toEqual({ tag_id: "tag-1" });
    expect(body.graph.edges).toHaveLength(1);
  });

  it("authors a live Assignment action with a specific active user", async () => {
    permissions.value.push("users:read");
    renderWorkspace();
    await screen.findByDisplayValue("Lead welcome");
    await waitFor(() => expect(get.mock.calls.some((call) => call[0] === "/api/v1/users")).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Assignment" }));
    expect(screen.getByText("Live contract")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Routing"), { target: { value: "user" } });
    expect(screen.getByLabelText("Assignee")).toHaveValue("11111111-1111-4111-8111-111111111111");
    expect(screen.getByText(/never replace an existing owner/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    const body = patch.mock.calls[0]![1].body;
    expect(body.graph.nodes.map((node: { kind: string }) => node.kind)).toEqual(["trigger", "assignment"]);
    expect(body.graph.nodes[1].config).toEqual({
      mode: "user",
      user_id: "11111111-1111-4111-8111-111111111111",
    });
    expect(body.graph.edges).toHaveLength(1);
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

  it("shows real trigger evidence without claiming an action ran", async () => {
    current = fixture({ status: "published", active_version_no: 1, has_unpublished_changes: false });
    receipts = [{
      id: "receipt-1", event_id: "event-1", event_type: "contact.created", event_version: 1,
      version_no: 1, status: "received", source: "contacts",
      occurred_at: "2026-07-30T12:30:00Z", received_at: "2026-07-30T12:30:00Z",
      processed_at: null,
    }];
    renderWorkspace();
    expect(await screen.findByText("Trigger receipts")).toBeVisible();
    expect(await screen.findByText("contact.created")).toBeVisible();
    expect(screen.getByText(/Conversation auto-resolved, Lead stage changed and Schedule receipts are durably dispatched/)).toBeVisible();
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
