import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutate = vi.fn();
const updateOrg = vi.fn();
const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map((day) => ({
  day,
  enabled: day !== "sunday",
  start: "10:30",
  end: "19:30",
}));
const policy = {
  assignment_mode: "manual",
  auto_mark_read: true,
  send_read_receipts: true,
  show_typing_indicators: false,
  working_hours: { enabled: true, days },
  automatic_replies: { welcome_enabled: true, welcome_body: "Welcome!", off_hours_enabled: false, off_hours_body: "" },
  auto_resolve: { enabled: false, inactive_after_hours: 24 },
  consent: { enabled: true, opt_in_keywords: ["START"], opt_out_keywords: ["STOP"] },
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
  useOrganization: () => ({ data: { row_version: 7, timezone: "Asia/Kolkata" } }),
  useUpdateOrganization: () => ({ mutate: updateOrg, isPending: false, error: null }),
}));

import { LiveChatSettings } from "./LiveChatSettings";

describe("LiveChatSettings", () => {
  beforeEach(() => {
    mutate.mockClear();
    updateOrg.mockClear();
    canManage = true;
  });

  it("shows the reference sections with the organisation timezone and closed days", () => {
    render(<LiveChatSettings />);
    expect(screen.getByRole("switch", { name: "Auto Resolve Chats" })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("switch", { name: "Manage Read Receipts" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByLabelText("Timezone")).toHaveValue("Asia/Kolkata");
    expect(screen.getByLabelText("Mon opens")).toHaveValue("10:30");
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("Welcome!")).toBeInTheDocument();
  });

  it("saves a toggle immediately and keeps the consent rules untouched", () => {
    render(<LiveChatSettings />);
    fireEvent.click(screen.getByRole("switch", { name: "Manage Read Receipts" }));
    const body = mutate.mock.calls[0]![0];
    expect(body.send_read_receipts).toBe(false);
    expect(body.consent).toEqual(policy.consent);
    expect(body).not.toHaveProperty("organization_timezone");
  });

  it("refuses an off-hours reply without message text", () => {
    render(<LiveChatSettings />);
    fireEvent.click(screen.getByRole("switch", { name: "Off Hours Message" }));
    expect(screen.getByRole("alert")).toHaveTextContent("off-hours reply needs message text");
    expect(mutate).not.toHaveBeenCalled();
  });

  it("configures the off-hours reply through the dialog", () => {
    render(<LiveChatSettings />);
    const replies = screen.getByRole("region", { name: "Automated replies" });
    fireEvent.click(within(replies).getAllByRole("button", { name: "Configure" })[1]!);
    const dialog = screen.getByRole("dialog", { name: "Configure Message" });
    fireEvent.click(within(dialog).getByRole("switch", { name: "Send off hours message" }));
    fireEvent.change(within(dialog).getByLabelText("Message"), { target: { value: "We are closed now." } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save Configuration" }));
    const body = mutate.mock.calls[0]![0];
    expect(body.automatic_replies.off_hours_enabled).toBe(true);
    expect(body.automatic_replies.off_hours_body).toBe("We are closed now.");
  });

  it("saves edited working hours and rejects a zero-length day", () => {
    render(<LiveChatSettings />);
    fireEvent.change(screen.getByLabelText("Mon closes"), { target: { value: "10:30" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Working Hours" }));
    expect(screen.getByRole("alert")).toHaveTextContent("different opening and closing times");
    fireEvent.change(screen.getByLabelText("Mon closes"), { target: { value: "18:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Working Hours" }));
    expect(mutate.mock.calls[0]![0].working_hours.days[0]).toEqual({ day: "monday", enabled: true, start: "10:30", end: "18:00" });
  });

  it("is read-only without settings:manage", () => {
    canManage = false;
    render(<LiveChatSettings />);
    expect(screen.queryByRole("button", { name: "Save Working Hours" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Configure" })).not.toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Auto Resolve Chats" })).toBeDisabled();
  });

  it("turns typing indicators on, and only while read receipts are on", () => {
    render(<LiveChatSettings />);
    const typing = screen.getByRole("switch", { name: "Show Typing Indicators" });
    fireEvent.click(typing);
    expect(mutate.mock.calls[0]![0].show_typing_indicators).toBe(true);
    fireEvent.click(screen.getByRole("switch", { name: "Manage Read Receipts" }));
    expect(screen.getByRole("switch", { name: "Show Typing Indicators" })).toBeDisabled();
    expect(screen.getByText(/Turn on read receipts first/)).toBeInTheDocument();
  });

  it("changes the workspace timezone through the organisation update", () => {
    render(<LiveChatSettings />);
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "Asia/Dubai" } });
    expect(updateOrg).toHaveBeenCalledWith({ timezone: "Asia/Dubai", row_version: 7 }, expect.anything());
  });
});
