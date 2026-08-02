import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CustomerProfile } from "@/features/customer-profile";
import { ConversationHistorySection } from "@/features/customer-profile/sections/ConversationHistorySection";

const testState = vi.hoisted(() => ({
  responses: new Map<string, unknown>(),
  errors: new Map<string, Error>(),
  permissions: new Map<string, boolean>(),
  calls: [] as Array<{ path: string; options: unknown }>,
}));

vi.mock("@/lib/api/client", () => {
  const GET = async (path: string, options?: unknown) => {
    testState.calls.push({ path, options });
    const error = testState.errors.get(path);
    if (error) return { error };
    return { data: testState.responses.get(path) };
  };
  const write = async () => ({ error: new Error("writes disabled in Customer 360 tests") });
  return {
    api: { GET, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

vi.mock("@/lib/auth", () => ({
  useHasPermission: (permission: string) => testState.permissions.get(permission) ?? true,
  useAuth: () => ({ hasPermission: (permission: string) => testState.permissions.get(permission) ?? true }),
}));

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

const contact = {
  id: "11111111-1111-4111-8111-111111111111",
  type: "contact",
  wa_id: "919876543210",
  phone_e164: "+919876543210",
  country_code: "IN",
  full_name: "Asha Mehta",
  first_name: "Asha",
  last_name: "Mehta",
  email: "asha@example.test",
  locale: "en_IN",
  profile_name: "Asha",
  opt_in_status: "opted_in",
  opt_in_at: "2026-07-01T08:00:00Z",
  opt_out_at: null,
  is_active_on_wa: true,
  last_inbound_at: "2026-08-02T08:00:00Z",
  last_outbound_at: "2026-08-02T08:10:00Z",
  last_contacted_at: "2026-08-02T08:10:00Z",
  source: "inbox",
  tags: [{ id: "tag-1", name: "Priority", color: "#28756f" }],
  attributes: { customer_circle: "Delhi" },
  created_at: "2026-07-01T08:00:00Z",
  updated_at: "2026-08-02T08:10:00Z",
  row_version: 3,
};

const conversation = {
  id: "22222222-2222-4222-8222-222222222222",
  type: "conversation",
  status: "open",
  channel_type: "whatsapp",
  assigned_to: "33333333-3333-4333-8333-333333333333",
  contact: { id: contact.id, name: contact.full_name, phone: contact.phone_e164 },
  tags: [],
  phone_number_id: "44444444-4444-4444-8444-444444444444",
  last_message_at: "2026-08-02T08:00:00Z",
  last_message_preview: "Please call tomorrow",
  unread_count: 1,
  window: { is_open: true, expires_at: "2026-08-03T08:00:00Z", last_inbound_at: "2026-08-02T08:00:00Z" },
  row_version: 1,
  created_at: "2026-08-01T08:00:00Z",
  updated_at: "2026-08-02T08:00:00Z",
};

beforeEach(() => {
  testState.responses.clear();
  testState.errors.clear();
  testState.permissions.clear();
  testState.calls.length = 0;
});

describe("CORE-07 Customer 360 convergence", () => {
  it("presents one accessible responsive workspace without placeholder modules", async () => {
    testState.responses.set("/api/v1/contacts/{contact_id}", contact);
    testState.responses.set("/api/v1/custom-attributes", [{ id: "attr-1", type: "attribute", key_name: "customer_circle", label: "Circle", data_type: "string", enum_values: null, is_indexed: true, is_pii: false, created_at: "2026-07-01T08:00:00Z", updated_at: "2026-07-01T08:00:00Z" }]);
    testState.responses.set("/api/v1/tags", []);

    withProviders(<CustomerProfile contactId={contact.id} />);

    expect(await screen.findByRole("heading", { name: "Asha Mehta" })).toBeInTheDocument();
    expect(screen.getByText("Single customer identity")).toBeInTheDocument();
    expect(screen.getByText("Delhi")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(8);
    expect(screen.queryByRole("tab", { name: /AI Assistant/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/no assignment/i)).not.toBeInTheDocument();

    const overview = screen.getByRole("tab", { name: /Overview/i });
    overview.focus();
    fireEvent.keyDown(overview, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: /Vi operations/i })).toHaveFocus();
    expect(screen.getByRole("tab", { name: /Vi operations/i })).toHaveAttribute("aria-selected", "true");
  });

  it("converges persisted Reactivation, reminder, note, KYC, SIM and Activation facts", async () => {
    testState.responses.set("/api/v1/contacts/{contact_id}", contact);
    testState.responses.set("/api/v1/custom-attributes", []);
    testState.responses.set("/api/v1/tags", []);
    testState.responses.set("/api/v1/reactivation-pipeline", {
      data: [{
        id: "case-1", contact_id: contact.id, stage: "activation_pending", owner_user_id: "owner-1", previous_vi_number: "9811111111", active_delhi_number: "9822222222", source: "referral", closed_reason: null, labels: ["priority", "follow_up"], row_version: 4, created_at: "2026-07-01T08:00:00Z", updated_at: "2026-08-02T08:00:00Z", available_transitions: ["completed"], contact_name: contact.full_name, contact_phone: contact.phone_e164, contact_email: contact.email, contact_attributes: {}, owner_name: "Ravi Agent", stage_entered_at: "2026-08-01T08:00:00Z", latest_eligibility_status: "eligible", latest_eligibility_reason: null, open_task_count: 1, overdue_task_count: 1, next_task_due_at: "2026-08-01T09:00:00Z", document_count: 2, verified_document_count: 2, sla_status: "breached", sla_due_at: "2026-08-01T09:00:00Z", reservation_status: "reserved", family_plan_required: true, family_numbers: ["9833333333"], conversion_indicator: "open", reminders: [{ id: "task-1", title: "Follow up", task_type: "reminder", priority: "high", status: "open", contact_id: contact.id, contact_name: contact.full_name, conversation_id: null, reference_type: "reactivation_case", reference_id: "case-1", assigned_agent_id: "owner-1", assigned_agent_name: "Ravi Agent", due_at: "2026-08-01T09:00:00Z", reminder_at: null, completed_at: null, outcome: null, description: null, row_version: 1, created_at: "2026-07-30T08:00:00Z", updated_at: "2026-07-30T08:00:00Z" }], follow_up_at: "2026-08-01T09:00:00Z", release_at: null, reminder_view: "overdue",
      }], total: 1, visible: 1, stage_counts: [], reminder_counts: { upcoming: 0, due_today: 0, overdue: 1 },
    });
    testState.responses.set("/api/v1/contacts/{contact_id}/kyc-cases", { data: [{ id: "kyc-1", reactivation_case_id: "case-1", contact_id: contact.id, status: "approved", owner_user_id: "owner-1", requester_user_id: "requester-1", holder_verified: true, delhi_presence_verified: true, active_delhi_number_verified: true, appointment_at: null, row_version: 2, created_at: "2026-07-01T08:00:00Z", updated_at: "2026-07-20T08:00:00Z" }], total: 1 });
    testState.responses.set("/api/v1/reactivation-cases/{case_id}/sim-orders", { data: [{ id: "sim-1", reactivation_case_id: "case-1", contact_id: contact.id, status: "delivered", delivery_address: "Delhi", service_area: "Delhi NCR", delivery_owner_user_id: "owner-1", dispatched_at: "2026-07-20T08:00:00Z", delivered_at: "2026-07-21T08:00:00Z", failed_at: null, failure_reason: null, sim_serial: "serial-redacted", customer_confirmed: true, row_version: 3, created_at: "2026-07-10T08:00:00Z", updated_at: "2026-07-21T08:00:00Z" }], total: 1 });
    testState.responses.set("/api/v1/reactivation-cases/{case_id}/activation-records", { data: [{ id: "activation-1", reactivation_case_id: "case-1", sim_order_id: "sim-1", contact_id: contact.id, status: "approved", owner_user_id: "owner-1", approval_reference: "approval-1", approved_by: "manager-1", approved_at: "2026-07-22T08:00:00Z", completed_at: null, rejection_reason: null, row_version: 2, created_at: "2026-07-21T08:00:00Z", updated_at: "2026-07-22T08:00:00Z" }], total: 1 });
    testState.responses.set("/api/v1/reactivation-cases/{case_id}/notes", { data: [{ id: 1, case_id: "case-1", actor_user_id: "owner-1", body: "Customer confirmed the preferred callback.", created_at: "2026-08-01T08:00:00Z" }] });

    withProviders(<CustomerProfile contactId={contact.id} />);
    fireEvent.click(await screen.findByRole("tab", { name: /Vi operations/i }));

    expect(await screen.findByText("Activation Pending")).toBeInTheDocument();
    expect(screen.getByText("Ravi Agent")).toBeInTheDocument();
    expect(await screen.findByText("Customer confirmed the preferred callback.")).toBeInTheDocument();
    expect(screen.getAllByText("Approved").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Delivered")).toBeInTheDocument();
    expect(screen.getByText("9833333333")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("uses the exact contact-scoped Inbox contract and reuses message history", async () => {
    testState.responses.set("/api/v1/conversations", { data: [conversation], page: { limit: 20, has_more: false, next_cursor: null } });
    testState.responses.set("/api/v1/conversations/{conversation_id}/messages", { data: [{ id: "message-1", type: "message", conversation_id: conversation.id, direction: "inbound", message_type: "text", status: "delivered", wamid: "wamid-1", content: { body: "Please call tomorrow" }, error_code: null, sent_at: null, delivered_at: "2026-08-02T08:00:00Z", read_at: null, created_at: "2026-08-02T08:00:00Z" }], page: { limit: 50, has_more: false, next_cursor: null } });

    const view = withProviders(<ConversationHistorySection contactId={contact.id} />);

    expect(await screen.findAllByText("Please call tomorrow")).not.toHaveLength(0);
    expect(screen.getByRole("button", { name: "Open in Inbox" })).toBeInTheDocument();
    expect(screen.getByRole("button", { pressed: true })).toBeInTheDocument();
    expect(view.container.firstElementChild?.className).toContain("lg:grid-cols-[18rem_minmax(0,1fr)]");
    const listCall = testState.calls.find((call) => call.path === "/api/v1/conversations");
    expect(listCall).toBeDefined();
    expect(listCall?.options).toMatchObject({ params: { query: { contact: contact.id } } });
  });

  it("shows permission-denied and recoverable error states without issuing unauthorized reads", async () => {
    testState.permissions.set("inbox:read", false);
    const restricted = withProviders(<ConversationHistorySection contactId={contact.id} />);
    expect(screen.getByText(/conversation history is restricted/i)).toBeInTheDocument();
    expect(testState.calls.some((call) => call.path === "/api/v1/conversations")).toBe(false);
    restricted.unmount();

    testState.permissions.set("inbox:read", true);
    testState.errors.set("/api/v1/conversations", new Error("Conversation service unavailable"));
    const second = withProviders(<ConversationHistorySection contactId={contact.id} />);
    expect(await screen.findByText("Conversation service unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    second.unmount();
  });

  it("keeps contact tags read-only when the role lacks contact-write permission", async () => {
    testState.permissions.set("contacts:write", false);
    testState.responses.set("/api/v1/contacts/{contact_id}", contact);
    testState.responses.set("/api/v1/custom-attributes", []);
    testState.responses.set("/api/v1/tags", []);

    withProviders(<CustomerProfile contactId={contact.id} />);

    expect(await screen.findByText(/Read-only: your role cannot change contact tags/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Remove tag Priority/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Add a tag/i)).not.toBeInTheDocument();
  });
});
