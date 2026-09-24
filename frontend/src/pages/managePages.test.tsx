import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const setPrefs = vi.fn();
vi.mock("@/features/inbox/messageAlerts", () => ({
  playChime: vi.fn(),
  useAlertPrefs: () => [{ sound: true, desktop: false }, setPrefs],
}));
vi.mock("@/features/notifications/NotificationSettingsPanel", () => ({ NotificationSettingsPanel: () => <p>categories</p> }));
vi.mock("@/components/layout", () => ({
  ManagePageHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
  MANAGE_PRIMARY_ACTION: "",
}));
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: { id: "u1" }, hasPermission: () => true }),
}));
const members = [
  { id: "u1", full_name: "Shailesh", email: "shail@vi.co", is_active: true, is_superuser: true, roles: [], last_login_at: new Date().toISOString() },
  { id: "u2", full_name: "Kamlesh", email: "kamlesh@vi.co", is_active: true, is_superuser: false, roles: ["manager"], last_login_at: null },
];
vi.mock("@/features/admin/api", () => ({
  useUsers: () => ({ data: { data: members }, isLoading: false, isError: false }),
  useSetUserActive: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}));
vi.mock("@/features/admin/UserFormDialog", () => ({ UserFormDialog: () => <p>form</p> }));

import { NotificationPreferencesPage } from "./NotificationPreferencesPage";
import { TeamPage } from "./TeamPage";

describe("Notification Preferences", () => {
  it("turns the sound off from the page", () => {
    render(<NotificationPreferencesPage />);
    fireEvent.click(screen.getByRole("switch", { name: "Sound notification" }));
    expect(setPrefs).toHaveBeenCalledWith({ sound: false, desktop: false });
  });
});

describe("Team", () => {
  it("shows one card per member with role and status", () => {
    render(<MemoryRouter><TeamPage /></MemoryRouter>);
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("Manager")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Never signed in")).toBeInTheDocument();
    // You cannot lock yourself out.
    expect(screen.queryByRole("button", { name: "Stop Shailesh signing in" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop Kamlesh signing in" })).toBeInTheDocument();
  });
});
