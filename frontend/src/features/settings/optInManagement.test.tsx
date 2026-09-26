import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutate = vi.fn();
const policy = {
  assignment_mode: "least_open",
  auto_mark_read: false,
  send_read_receipts: true,
  working_hours: { enabled: true, days: [] },
  automatic_replies: { welcome_enabled: true, welcome_body: "Hi", off_hours_enabled: false, off_hours_body: "" },
  auto_resolve: { enabled: true, inactive_after_hours: 24 },
  consent: {
    enabled: true,
    opt_in_keywords: ["START"],
    opt_out_keywords: ["STOP"],
    opt_in_response_enabled: false,
    opt_in_response_body: "",
    opt_out_response_enabled: true,
    opt_out_response_body: "You have been opted out.",
  },
  configured: true,
  updated_at: null,
  organization_timezone: "Asia/Kolkata",
};
let canManage = true;

vi.mock("@/features/settings/api", () => ({
  apiErrorMessage: () => "error",
  useHasPermission: () => canManage,
  useInboxOperations: () => ({ data: policy, isLoading: false, isError: false }),
  useUpdateInboxOperations: () => ({ mutate, isPending: false, isSuccess: false, error: null }),
}));

import { OptInManagement } from "./OptInManagement";

describe("OptInManagement", () => {
  beforeEach(() => {
    mutate.mockClear();
    canManage = true;
  });

  it("shows each keyword in its own field and the configured response preview", () => {
    render(<OptInManagement />);
    expect(screen.getByLabelText("Opt-out Keywords 1")).toHaveValue("STOP");
    expect(screen.getByLabelText("Opt-in Keywords 1")).toHaveValue("START");
    expect(screen.getByText("You have been opted out.")).toBeInTheDocument();
  });

  it("saves added keywords without touching the rest of the inbox policy", () => {
    render(<OptInManagement />);
    const optOut = screen.getByRole("region", { name: "Opt-out Keywords" });
    fireEvent.click(within(optOut).getByRole("button", { name: "Add more" }));
    fireEvent.change(screen.getByLabelText("Opt-out Keywords 2"), { target: { value: " unsubscribe " } });
    fireEvent.click(within(optOut).getByRole("button", { name: "Save Settings" }));
    const body = mutate.mock.calls[0]![0];
    expect(body.consent.opt_out_keywords).toEqual(["STOP", "unsubscribe"]);
    expect(body.auto_resolve).toEqual(policy.auto_resolve);
    expect(body.assignment_mode).toBe("least_open");
    expect(body).not.toHaveProperty("configured");
  });

  it("refuses a keyword that is both opt-in and opt-out", () => {
    render(<OptInManagement />);
    fireEvent.change(screen.getByLabelText("Opt-in Keywords 1"), { target: { value: "stop" } });
    fireEvent.click(within(screen.getByRole("region", { name: "Opt-in Keywords" })).getByRole("button", { name: "Save Settings" }));
    expect(screen.getByRole("alert")).toHaveTextContent("cannot be both");
    expect(mutate).not.toHaveBeenCalled();
  });

  it("configures a response through the dialog", () => {
    render(<OptInManagement />);
    fireEvent.click(within(screen.getByRole("region", { name: "Opt-in Keywords" })).getByRole("button", { name: "Configure" }));
    const dialog = screen.getByRole("dialog", { name: "Configure Message" });
    fireEvent.click(within(dialog).getByRole("switch", { name: "Send opt-in response" }));
    fireEvent.change(within(dialog).getByLabelText("Message"), { target: { value: "Welcome back!" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save Configuration" }));
    const body = mutate.mock.calls[0]![0];
    expect(body.consent.opt_in_response_enabled).toBe(true);
    expect(body.consent.opt_in_response_body).toBe("Welcome back!");
  });

  it("is read-only without settings:manage", () => {
    canManage = false;
    render(<OptInManagement />);
    expect(screen.queryByRole("button", { name: "Save Settings" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Opt-out Keywords 1")).toBeDisabled();
    expect(screen.getByRole("switch", { name: "Recognize consent keywords" })).toBeDisabled();
  });
});
