import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationCenter } from "@/features/notifications/NotificationCenter";

const state = vi.hoisted(() => ({
  query: {} as Record<string, unknown>,
  list: {
    data: undefined as unknown,
    isLoading: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
  markRead: vi.fn(),
  markAll: vi.fn(),
}));

vi.mock("@/features/notifications/api", () => ({
  useNotifications: (query: Record<string, unknown>) => {
    state.query = query;
    return state.list;
  },
  useMarkNotificationRead: () => ({ mutate: state.markRead, isPending: false }),
  useMarkAllNotificationsRead: () => ({ mutate: state.markAll, isPending: false }),
}));

vi.mock("@/features/admin/api", () => ({
  useUsers: () => ({
    data: { data: [{ id: "user-2", full_name: "Arjun Rao", is_active: true }] },
  }),
}));

const notification = {
  id: "notification-1",
  type: "follow_up_due",
  title: "Follow-up is due",
  body: "A customer follow-up needs attention.",
  read_status: "unread",
  lifecycle_status: "overdue",
  due_at: "2026-08-01T09:00:00Z",
  read_at: null,
  resolved_at: null,
  created_at: "2026-08-02T08:00:00Z",
  recipient: { id: "user-1", name: "Priya Shah" },
  actor: null,
  contact: { id: "contact-1", name: "Asha Mehta" },
  reactivation_case: { id: "case-1", name: null },
  task: { id: "task-1", name: null },
};

function RouteProbe(): JSX.Element {
  const current = useLocation();
  return <output>route:{current.pathname}{current.search}</output>;
}

function renderCenter(overrides: Partial<React.ComponentProps<typeof NotificationCenter>> = {}) {
  const props = {
    open: true,
    onClose: vi.fn(),
    canRead: true,
    canViewTeam: true,
    canViewUsers: true,
    systemSignals: [],
    canViewSystem: false,
    ...overrides,
  };
  return {
    props,
    ...render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="*" element={<><NotificationCenter {...props} /><RouteProbe /></>} />
        </Routes>
      </MemoryRouter>,
    ),
  };
}

describe("NotificationCenter", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    state.list = { data: { data: [notification], page: { limit: 100, has_more: false } }, isLoading: false, isError: false, error: null, refetch: vi.fn() };
    state.markRead.mockReset();
    state.markAll.mockReset();
  });

  it("renders the dense responsive workflow, filters, persisted actions and deep links", async () => {
    const { props } = renderCenter();
    const dialog = screen.getByRole("dialog", { name: "Notification center" });
    expect(dialog).toHaveClass("w-full", "sm:max-w-xl");
    expect(screen.getByText("Asha Mehta")).toBeInTheDocument();
    expect(screen.getByText("overdue")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "follow_up_due" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "unread" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark all read" }));
    expect(state.markAll).toHaveBeenCalledWith(undefined);
    fireEvent.click(screen.getByRole("button", { name: "Task" }));
    expect(state.markRead).toHaveBeenCalledWith("notification-1");
    expect(screen.getByText("route:/tasks?task=task-1")).toBeInTheDocument();
    expect(props.onClose).toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Assignee"), { target: { value: "user-2" } });
    await waitFor(() => expect(state.query).toMatchObject({ type: "follow_up_due", status: "unread", assignee_id: "user-2" }));
    expect(screen.getByText("Read-only team view")).toBeInTheDocument();
  });

  it("manages focus and Escape dismissal and keeps team data permission-aware", () => {
    const { props } = renderCenter({ canViewTeam: false, canViewUsers: false });
    expect(screen.getByRole("dialog", { name: "Notification center" })).toHaveFocus();
    expect(screen.queryByLabelText("Assignee")).not.toBeInTheDocument();
    expect(screen.getByText("Showing notifications assigned to you")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(props.onClose).toHaveBeenCalled();
  });

  it("shows honest permission, loading, empty, error and offline states", () => {
    const permission = renderCenter({ canRead: false });
    expect(screen.getByText("Notifications unavailable")).toBeInTheDocument();
    permission.unmount();

    state.list = { data: undefined, isLoading: true, isError: false, error: null, refetch: vi.fn() };
    const loading = renderCenter();
    expect(screen.getByLabelText("Loading notifications")).toBeInTheDocument();
    loading.unmount();

    state.list = { data: { data: [], page: { limit: 100, has_more: false } }, isLoading: false, isError: false, error: null, refetch: vi.fn() };
    const empty = renderCenter();
    expect(screen.getByText("You are all caught up")).toBeInTheDocument();
    empty.unmount();

    state.list = { data: undefined, isLoading: false, isError: true, error: new Error("Service unavailable"), refetch: vi.fn() };
    const error = renderCenter();
    expect(screen.getByRole("alert")).toHaveTextContent("Service unavailable");
    fireEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Retry" }));
    expect(state.list.refetch).toHaveBeenCalled();
    error.unmount();

    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    renderCenter();
    expect(screen.getByText(/You are offline/)).toBeInTheDocument();
  });
});
