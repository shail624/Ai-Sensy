import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { KycOperationsWorkspace } from "@/features/kyc/KycOperationsWorkspace";

const mocks = vi.hoisted(() => ({
  permissions: { value: ["kyc:read", "kyc:write", "kyc:decide", "kyc:approve", "tasks:write", "documents:read", "users:read"] },
  state: { value: {} as Record<string, unknown> },
  refetch: vi.fn(),
  update: vi.fn(),
  setDocument: vi.fn(),
  schedule: vi.fn(),
  review: vi.fn(),
  approve: vi.fn(),
  complete: vi.fn(),
  cancel: vi.fn(),
  reschedule: vi.fn(),
}));

const card = {
  id: "kyc-1",
  reactivation_case_id: "case-1",
  contact_id: "contact-1",
  status: "under_review" as const,
  owner_user_id: "user-1",
  requester_user_id: "user-1",
  holder_verified: true,
  delhi_presence_verified: false,
  active_delhi_number_verified: true,
  appointment_at: "2026-08-04T10:00:00Z",
  row_version: 4,
  created_at: "2026-08-01T08:00:00Z",
  updated_at: "2026-08-02T08:00:00Z",
  contact_name: "Asha Mehra",
  contact_phone: "+919811111111",
  contact_email: "asha@example.test",
  owner_name: "Priya Shah",
  reactivation_stage: "kyc_verification" as const,
  checklist: [{ id: "ref-1", kyc_case_id: "kyc-1", purpose: "aadhaar" as const, document_id: "doc-1", document_title: "Aadhaar protected proof", document_type: "identity", document_status: "verified", row_version: 0, created_at: "2026-08-02T08:00:00Z", updated_at: "2026-08-02T08:00:00Z" }],
  checklist_complete: false,
  progress_percent: 60,
  latest_review: { id: "decision-1", kyc_case_id: "kyc-1", decision_type: "review" as const, decision: "approved" as const, reason_code: null, reason: null, decided_by: "user-2", decided_at: "2026-08-02T09:00:00Z" },
  latest_manager_decision: null,
  appointments: [{ id: "task-1", title: "KYC verification appointment", status: "open", due_at: "2026-08-04T10:00:00Z", reminder_at: null, assigned_agent_id: "user-2", assigned_agent_name: "Arjun Rao", row_version: 1 }],
  sla_status: "on_track" as const,
  sla_due_at: "2026-08-04T12:00:00Z",
};

vi.mock("@/lib/auth", () => ({
  useHasPermission: (code: string) => mocks.permissions.value.includes(code),
  useAuth: () => ({ user: { id: "user-3", full_name: "Manager" } }),
}));
vi.mock("@/features/admin/api", () => ({ useUsers: () => ({ data: { data: [{ id: "user-1", full_name: "Priya Shah", is_active: true }, { id: "user-2", full_name: "Arjun Rao", is_active: true }] } }) }));
vi.mock("@/features/documents", () => ({ DocumentWorkspace: () => <div>Protected Document Center</div> }));
vi.mock("@/features/documents/api", () => ({ useContactDocuments: () => ({ data: { data: [{ id: "doc-1", title: "Aadhaar protected proof", document_type: "identity", status: "verified" }, { id: "doc-2", title: "PAN protected proof", document_type: "identity", status: "verified" }] }, isLoading: false, isError: false, error: null, refetch: vi.fn() }) }));
vi.mock("@/features/tasks/api", () => ({
  useCompleteTask: () => ({ mutate: mocks.complete, isPending: false, error: null }),
  useCancelTask: () => ({ mutate: mocks.cancel, isPending: false, error: null }),
  useRescheduleTask: () => ({ mutate: mocks.reschedule, isPending: false, error: null }),
}));
vi.mock("@/features/kyc/api", () => ({
  apiErrorMessage: (error: unknown) => error instanceof Error ? error.message : "Request failed",
  useKycOperations: () => mocks.state.value,
  useUpdateKycCase: () => ({ mutate: mocks.update, isPending: false, error: null }),
  useSetKycDocumentReference: () => ({ mutate: mocks.setDocument, isPending: false, error: null }),
  useCreateKycAppointment: () => ({ mutate: mocks.schedule, isPending: false, error: null }),
  useKycDecisions: () => ({ data: [card.latest_review], isLoading: false, isError: false, error: null, refetch: vi.fn() }),
  useRecordKycReview: () => ({ mutate: mocks.review, isPending: false, error: null }),
  useRecordKycApproval: () => ({ mutate: mocks.approve, isPending: false, error: null }),
}));

function ready(data = [card]) { return { data: { data, total: data.length }, isLoading: false, isError: false, isFetching: false, error: null, refetch: mocks.refetch }; }
function renderWorkspace() { return render(<MemoryRouter><KycOperationsWorkspace /></MemoryRouter>); }

beforeEach(() => {
  mocks.permissions.value = ["kyc:read", "kyc:write", "kyc:decide", "kyc:approve", "tasks:write", "documents:read", "users:read"];
  mocks.state.value = ready();
  Object.values(mocks).forEach((value) => { if (typeof value === "function" && "mockReset" in value) value.mockReset(); });
});

describe("CORE-04 governed KYC workspace", () => {
  it("renders dense factual queue and responsive transformation without mock records", () => {
    const { container } = renderWorkspace();
    expect(screen.getAllByText("Asha Mehra").length).toBeGreaterThan(0);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByText("60%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1/2 linked").length).toBeGreaterThan(0);
    expect(container.querySelector(".md\\:hidden")).not.toBeNull();
    expect(screen.queryByText(/sample|mock lead/i)).not.toBeInTheDocument();
  });

  it("opens the accessible drawer by keyboard and updates persisted verification checks", () => {
    renderWorkspace();
    const row = screen.getAllByText("Asha Mehra")[0]!.closest("tr")!;
    fireEvent.keyDown(row, { key: "Enter" });
    expect(screen.getByRole("dialog", { name: "Asha Mehra · KYC" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /Delhi presence verified/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save verification" }));
    expect(mocks.update).toHaveBeenCalledWith(expect.objectContaining({ kycId: "kyc-1", expectedRowVersion: 4, delhiPresenceVerified: true }));
  });

  it("links protected evidence, schedules Task-backed appointments and exposes separated decisions", () => {
    renderWorkspace();
    fireEvent.click(screen.getAllByText("Asha Mehra")[0]!.closest("tr")!);
    fireEvent.click(screen.getAllByRole("tab", { name: /Documents/ })[1]!);
    expect(screen.getByText("Protected Document Center")).toBeInTheDocument();
    const panSelect = screen.getByLabelText("Select PAN proof");
    fireEvent.change(panSelect, { target: { value: "doc-2" } });
    expect(mocks.setDocument).toHaveBeenCalledWith(expect.objectContaining({ purpose: "pan", documentId: "doc-2", expectedRowVersion: 4 }));
    fireEvent.click(screen.getByRole("tab", { name: /Appointments/ }));
    expect(screen.getByText(/shared Task authority/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Date and time"), { target: { value: "2026-08-06T10:30" } });
    fireEvent.click(screen.getByRole("button", { name: "Schedule" }));
    expect(mocks.schedule).toHaveBeenCalledWith(expect.objectContaining({ kycId: "kyc-1", expectedRowVersion: 4 }), expect.any(Object));
    fireEvent.click(screen.getByRole("tab", { name: /Decisions/ }));
    expect(screen.getByText("Separation of duties")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record manager decision" })).toBeInTheDocument();
  });

  it("renders loading, empty, recoverable error and permission-denied states", () => {
    mocks.state.value = { ...ready(), data: undefined, isLoading: true };
    const loading = renderWorkspace();
    expect(screen.getByLabelText("Loading KYC cases")).toBeInTheDocument();
    loading.unmount();
    mocks.state.value = ready([]);
    const empty = renderWorkspace();
    expect(screen.getByText("No KYC cases yet")).toBeInTheDocument();
    empty.unmount();
    mocks.state.value = { ...ready(), data: undefined, isError: true, error: new Error("KYC queue unavailable") };
    const failed = renderWorkspace();
    expect(screen.getByText("KYC queue unavailable")).toBeInTheDocument();
    failed.unmount();
    mocks.permissions.value = [];
    const restricted = renderWorkspace();
    expect(screen.getByText("KYC operations are restricted")).toBeInTheDocument();
    restricted.unmount();
  });
});
