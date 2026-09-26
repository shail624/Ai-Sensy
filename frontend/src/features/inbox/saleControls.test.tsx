import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const saleMutate = vi.fn();
const taskMutate = vi.fn();

vi.mock("@/features/inbox/api", () => ({
  apiErrorMessage: () => "error",
  useUpdateSaleDetails: () => ({ mutate: saleMutate, isPending: false, error: null }),
}));
vi.mock("@/features/tasks/api", () => ({
  useCreateTask: () => ({ mutate: taskMutate, isPending: false, error: null }),
}));
vi.mock("@/features/inbox/NotesPanel", () => ({ NotesPanel: () => <p>notes</p> }));
vi.mock("@/lib/auth", () => ({ useHasPermission: () => true }));

import { ChannelBadge } from "./ChannelBadge";
import { SaleControls } from "./SaleControls";
import { formatDay } from "./saleStatus";

const conversation = {
  id: "conv-1",
  connector_type: "waha",
  contact: { id: "contact-1", name: "Shailesh", phone: "+919891000010", sale_status: "follow_up", release_date: "2026-10-05" },
} as never;

describe("SaleControls", () => {
  beforeEach(() => {
    saleMutate.mockReset();
    taskMutate.mockReset();
  });

  it("shows the current status and release date, and changes the status", () => {
    render(<SaleControls conversation={conversation} />);
    const select = screen.getByLabelText("Sale status") as HTMLSelectElement;
    expect(select.value).toBe("follow_up");
    expect(screen.getByRole("button", { name: /Release: 5 Oct 2026/ })).toBeInTheDocument();

    fireEvent.change(select, { target: { value: "not_interested" } });
    expect(saleMutate).toHaveBeenCalledWith({ sale_status: "not_interested" });
    fireEvent.change(select, { target: { value: "" } });
    expect(saleMutate).toHaveBeenLastCalledWith({ sale_status: null });
  });

  it("creates a reminder task for this chat", () => {
    render(<SaleControls conversation={conversation} />);
    fireEvent.click(screen.getByRole("button", { name: /Reminder/ }));
    fireEvent.change(screen.getByLabelText("Date"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("Time"), { target: { value: "11:30" } });
    fireEvent.change(screen.getByLabelText("What to do"), { target: { value: "Call back" } });
    fireEvent.click(screen.getByRole("button", { name: "Set reminder" }));

    const body = taskMutate.mock.calls[0]?.[0];
    expect(body).toMatchObject({
      contact_id: "contact-1",
      conversation_id: "conv-1",
      task_type: "reminder",
      title: "Call back",
      due_at: new Date("2026-10-01T11:30").toISOString(),
    });
  });

  it("clears the release date", () => {
    render(<SaleControls conversation={conversation} />);
    fireEvent.click(screen.getByRole("button", { name: /Release:/ }));
    fireEvent.click(screen.getByRole("button", { name: /Remove date/ }));
    expect(saleMutate.mock.calls[0]?.[0]).toEqual({ release_date: null });
  });
});

describe("ChannelBadge", () => {
  it("labels QR and API chats plainly", () => {
    const { rerender } = render(<ChannelBadge conversation={{ connector_type: "waha" }} />);
    expect(screen.getByText("QR")).toBeInTheDocument();
    rerender(<ChannelBadge conversation={{ connector_type: "meta_cloud" }} />);
    expect(screen.getByText("API")).toBeInTheDocument();
  });

  it("formats server dates without a timezone shift", () => {
    expect(formatDay("2026-01-01")).toBe("1 Jan 2026");
  });
});
