import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReactivationPipelineBoard } from "@/features/reactivation/ReactivationPipelineBoard";
import type { ReactivationCard, ReactivationFilters } from "@/features/reactivation/types";

const mocks = vi.hoisted(() => ({
  permissions: {
    value: [
      "reactivation:read",
      "reactivation:write",
      "reactivation:transition",
      "users:read",
      "tasks:read",
      "tasks:write",
      "documents:read",
    ],
  },
  pipelineState: { value: {} as Record<string, unknown> },
  filters: { value: {} as ReactivationFilters },
  refetch: vi.fn(),
  transition: vi.fn(),
  update: vi.fn(),
  addNote: vi.fn(),
  recordEligibility: vi.fn(),
  createKyc: vi.fn(),
}));

const card: ReactivationCard = {
  id: "case-1",
  contact_id: "contact-1",
  stage: "new_lead",
  available_transitions: ["lead_confirmed", "not_required"],
  owner_user_id: "user-1",
  previous_vi_number: "9811111111",
  active_delhi_number: "9822222222",
  source: "campaign",
  closed_reason: null,
  row_version: 2,
  created_at: "2026-08-01T08:00:00Z",
  updated_at: "2026-08-02T08:00:00Z",
  contact_name: "Asha Mehra",
  contact_phone: "+919811111111",
  contact_email: "asha@example.test",
  contact_attributes: { family_plan_required: true },
  owner_name: "Priya Shah",
  stage_entered_at: "2026-08-02T08:00:00Z",
  latest_eligibility_status: "review_required" as const,
  latest_eligibility_reason: "Manual document review",
  open_task_count: 2,
  overdue_task_count: 1,
  next_task_due_at: "2026-08-02T10:00:00Z",
  document_count: 3,
  verified_document_count: 2,
  sla_status: "breached" as const,
  sla_due_at: "2026-08-02T07:00:00Z",
  reservation_status: "Awaiting confirmation",
  family_plan_required: true,
  family_numbers: ["+919822222221"],
  conversion_indicator: "open" as const,
  labels: ["follow_up", "priority"],
  reminders: [],
  follow_up_at: "2026-08-03T10:00:00Z",
  release_at: null,
  reminder_view: "upcoming" as const,
};

const stageCounts = [
  "new_lead",
  "lead_confirmed",
  "documents_pending",
  "documents_received",
  "kyc_verification",
  "sim_required",
  "activation_pending",
  "completed",
  "not_required",
].map((stage) => ({ stage, count: stage === "new_lead" ? 1 : 0 }));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (code: string) => mocks.permissions.value.includes(code),
  useAuth: () => ({ user: { id: "user-1", full_name: "Priya Shah" } }),
}));

vi.mock("@/features/admin/api", () => ({
  useUsers: () => ({
    data: {
      data: [
        { id: "user-1", full_name: "Priya Shah", is_active: true },
        { id: "user-2", full_name: "Arjun Rao", is_active: true },
      ],
    },
  }),
}));

vi.mock("@/features/documents", () => ({
  DocumentWorkspace: () => <div>Persisted document workspace</div>,
}));

vi.mock("@/features/tasks/TasksSectionForProfile", () => ({
  TasksSectionForProfile: () => <div>Persisted task workspace</div>,
}));

vi.mock("@/features/kyc/api", () => ({
  apiErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
  useContactKycCases: () => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useCreateKycCase: () => ({ mutate: mocks.createKyc, isPending: false, error: null }),
}));

vi.mock("@/features/reactivation/api", () => ({
  apiErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
  useReactivationPipeline: (filters: ReactivationFilters) => {
    mocks.filters.value = filters;
    return mocks.pipelineState.value;
  },
  useTransitionReactivation: () => ({
    mutate: mocks.transition,
    isPending: false,
    error: null,
  }),
  useUpdateReactivation: () => ({ mutate: mocks.update, isPending: false, error: null }),
  useReactivationEvents: () => ({
    data: [
      {
        id: "event-1",
        case_id: "case-1",
        from_stage: null,
        to_stage: "new_lead",
        actor_user_id: "user-1",
        reason: null,
        created_at: "2026-08-01T08:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useReactivationNotes: () => ({
    data: [
      {
        id: 1,
        case_id: "case-1",
        actor_user_id: "user-1",
        body: "Customer prefers a weekday callback",
        created_at: "2026-08-02T09:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useAddReactivationNote: () => ({
    mutate: mocks.addNote,
    isPending: false,
    error: null,
  }),
  useEligibilityChecks: () => ({
    data: [
      {
        id: "check-1",
        case_id: "case-1",
        status: "review_required",
        source: "manual",
        reason: "Manual document review",
        approval_reference: null,
        checked_by: "user-1",
        checked_at: "2026-08-02T08:30:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useRecordEligibility: () => ({
    mutate: mocks.recordEligibility,
    isPending: false,
    error: null,
  }),
}));

function readyState(data = [card], total = data.length) {
  return {
    data: {
      data,
      total,
      visible: data.length,
      stage_counts: stageCounts,
      reminder_counts: { upcoming: data.length, due_today: 0, overdue: 0 },
    },
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: mocks.refetch,
  };
}

function renderBoard(initialEntry = "/reactivation/pipeline") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ReactivationPipelineBoard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mocks.permissions.value = [
    "reactivation:read",
    "reactivation:write",
    "reactivation:transition",
    "users:read",
    "tasks:read",
    "tasks:write",
    "documents:read",
  ];
  mocks.pipelineState.value = readyState();
  mocks.filters.value = {};
  mocks.refetch.mockReset();
  mocks.transition.mockReset();
  mocks.update.mockReset();
  mocks.addNote.mockReset();
  mocks.recordEligibility.mockReset();
  mocks.createKyc.mockReset();
});

describe("governed Reactivation pipeline", () => {
  it("renders all approved stages and factual persisted cards without the former mock shell", () => {
    renderBoard();
    expect(screen.getByText("Asha Mehra")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "New Lead" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Not Required" })).toBeInTheDocument();
    for (const stage of [
      "New Lead",
      "Lead Confirmed",
      "Documents Pending",
      "Documents Received",
      "KYC / Verification",
      "SIM Required",
      "Activation Pending",
      "Completed",
      "Not Required",
    ]) {
      expect(screen.getByRole("region", { name: stage })).toBeInTheDocument();
    }
    expect(screen.queryByText(/No verified cards/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reference only/i)).not.toBeInTheDocument();
  });

  it("supports keyboard and drag movement through the same governed confirmation", () => {
    renderBoard();
    const caseCard = screen.getByLabelText("Asha Mehra, New Lead");
    fireEvent.keyDown(caseCard, { key: "ArrowRight", altKey: true });
    expect(screen.getByRole("dialog", { name: "Move to Lead Confirmed" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm move" }));
    expect(mocks.transition).toHaveBeenCalledWith(
      expect.objectContaining({
        card: expect.objectContaining({ id: "case-1", row_version: 2 }),
        toStage: "lead_confirmed",
      }),
      expect.any(Object),
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.dragStart(caseCard);
    fireEvent.drop(screen.getByRole("region", { name: "Lead Confirmed" }));
    expect(screen.getByRole("dialog", { name: "Move to Lead Confirmed" })).toBeInTheDocument();
  });

  it("keeps server data visible across refresh and provides the responsive list transformation", () => {
    const { container } = renderBoard();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(mocks.refetch).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Asha Mehra")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "List view" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.querySelector(".md\\:hidden")).not.toBeNull();
  });

  it("persists operational filters and pagination in the URL-backed query contract", () => {
    mocks.pipelineState.value = readyState([card], 60);
    renderBoard(
      "/reactivation/pipeline?q=Asha&stage=new_lead&reminder=overdue&view=list&page=2",
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Asha")).toBeInTheDocument();
    expect(mocks.filters.value).toEqual(
      expect.objectContaining({
        q: "Asha",
        stage: ["new_lead"],
        reminder_view: "overdue",
        offset: 25,
        limit: 25,
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(mocks.filters.value.offset).toBe(50);
    fireEvent.change(screen.getByLabelText("Filter by status"), {
      target: { value: "completed" },
    });
    expect(mocks.filters.value.offset).toBe(0);
    expect(mocks.filters.value.stage).toEqual(["completed"]);
  });

  it("uses factual work views without claiming server-shared saved views", () => {
    renderBoard();
    fireEvent.click(screen.getAllByRole("button", { name: "Overdue" })[0]!);
    expect(mocks.filters.value.reminder_view).toBe("overdue");
    expect(
      screen.getByText(/Team-shared saved views remain a later milestone/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Completed" })[0]!);
    expect(mocks.filters.value.stage).toEqual(["completed"]);
    expect(mocks.filters.value.reminder_view).toBeUndefined();
  });

  it("opens accessible case details with assignment, evidence, notes, tasks and documents", async () => {
    renderBoard();
    fireEvent.click(screen.getByRole("button", { name: /Asha Mehra/ }));
    expect(screen.getByRole("dialog", { name: /Asha Mehra · New Lead/ })).toBeInTheDocument();
    expect(screen.getByText("Awaiting confirmation")).toBeInTheDocument();
    expect(screen.getAllByText("Follow-up").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Priority").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Manual document review")).toHaveLength(2);
    expect(screen.getByText("+919822222221")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Assigned owner"), {
      target: { value: "user-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Follow-up" }));
    expect(screen.queryByLabelText("Next follow-up date")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save case" }));
    expect(mocks.update).toHaveBeenCalledWith(
      expect.objectContaining({
        ownerUserId: "user-2",
        labels: ["priority"],
        followUpAt: null,
        card: expect.objectContaining({ row_version: 2 }),
      }),
    );

    fireEvent.click(screen.getByRole("tab", { name: /History/ }));
    expect(screen.getByText("Immutable stage history")).toBeInTheDocument();
    expect(screen.getByText("Customer prefers a weekday callback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Tasks/ }));
    expect(screen.getByText("Persisted task workspace")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Documents/ }));
    await waitFor(() =>
      expect(screen.getByText("Persisted document workspace")).toBeInTheDocument(),
    );
  });

  it("renders truthful loading, empty, error and permission-aware states", () => {
    mocks.pipelineState.value = { ...readyState(), data: undefined, isLoading: true };
    const loading = renderBoard();
    expect(screen.getByLabelText("Loading reactivation pipeline")).toBeInTheDocument();
    loading.unmount();

    mocks.pipelineState.value = readyState([]);
    const empty = renderBoard();
    expect(screen.getByText("No reactivation cases yet")).toBeInTheDocument();
    empty.unmount();

    mocks.pipelineState.value = {
      ...readyState(),
      data: undefined,
      isError: true,
      error: new Error("Pipeline unavailable"),
    };
    const failed = renderBoard();
    expect(screen.getByText("Pipeline unavailable")).toBeInTheDocument();
    failed.unmount();

    mocks.pipelineState.value = readyState();
    mocks.permissions.value = ["reactivation:read"];
    const restricted = renderBoard();
    expect(screen.getByLabelText("Asha Mehra, New Lead")).toHaveAttribute(
      "draggable",
      "false",
    );
    fireEvent.click(screen.getByRole("button", { name: /Asha Mehra/ }));
    expect(
      screen.getByText("Your role can review this case but cannot move it."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save case" })).not.toBeInTheDocument();
    restricted.unmount();
  });

  it("does not advertise terminal cards as draggable work", () => {
    mocks.pipelineState.value = readyState([
      {
        ...card,
        stage: "completed",
        available_transitions: [],
        conversion_indicator: "converted",
      },
    ]);
    renderBoard();
    expect(screen.getByLabelText("Asha Mehra, Completed")).toHaveAttribute(
      "draggable",
      "false",
    );
  });

  it("opens KYC from a document-ready persisted Reactivation case", () => {
    mocks.permissions.value.push("kyc:read", "kyc:write");
    mocks.pipelineState.value = readyState([
      {
        ...card,
        stage: "documents_received" as const,
        available_transitions: ["kyc_verification" as const],
      },
    ]);
    renderBoard();
    fireEvent.click(screen.getByRole("button", { name: /Asha Mehra/ }));
    fireEvent.click(screen.getByRole("tab", { name: /KYC/ }));
    fireEvent.click(screen.getByRole("button", { name: "Create KYC case" }));
    expect(mocks.createKyc).toHaveBeenCalledWith({
      caseId: "case-1",
      ownerUserId: "user-1",
    });
  });
});
