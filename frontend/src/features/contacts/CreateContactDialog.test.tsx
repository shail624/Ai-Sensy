import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CreateContactDialog } from "./CreateContactDialog";

const state = vi.hoisted(() => ({ mutate: vi.fn(), isPending: false, error: null as Error | null }));
vi.mock("@/features/contacts/api", () => ({ useCreateContact: () => state }));

describe("CreateContactDialog", () => {
  beforeEach(() => { state.mutate.mockReset(); state.isPending = false; state.error = null; });
  it("validates a name and international phone before submitting", () => {
    render(<CreateContactDialog onClose={vi.fn()} onCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Add Contact" }));
    expect(screen.getByRole("alert")).toHaveTextContent("valid international");
    expect(state.mutate).not.toHaveBeenCalled();
  });
  it("saves trimmed values without assuming consent and only completes after success", () => {
    const onCreated = vi.fn();
    render(<CreateContactDialog onClose={vi.fn()} onCreated={onCreated} />);
    fireEvent.change(screen.getByLabelText("Name *"), { target: { value: " Asha " } });
    fireEvent.change(screen.getByLabelText("Mobile Number *"), { target: { value: " +919876543210 " } });
    fireEvent.click(screen.getByRole("button", { name: "Add Contact" }));
    expect(state.mutate).toHaveBeenCalledWith({ full_name: "Asha", phone_e164: "+919876543210", source: "manual", opt_in_status: "unknown" }, { onSuccess: onCreated });
    expect(onCreated).not.toHaveBeenCalled();
    state.mutate.mock.calls[0]?.[1].onSuccess();
    expect(onCreated).toHaveBeenCalledOnce();
  });
  it("prevents dismissal and duplicate submission while saving", () => {
    state.isPending = true;
    const onClose = vi.fn();
    render(<CreateContactDialog onClose={onClose} onCreated={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
    expect(state.mutate).not.toHaveBeenCalled();
  });
  it("keeps server errors visible for correction", () => {
    state.error = new Error("This number already exists");
    render(<CreateContactDialog onClose={vi.fn()} onCreated={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("This number already exists");
  });
});
