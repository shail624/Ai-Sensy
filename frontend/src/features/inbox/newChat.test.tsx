import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutate = vi.fn();
let startError: unknown = null;

vi.mock("@/features/inbox/api", () => ({
  apiErrorMessage: (error: { detail?: string }) => error.detail ?? "error",
  useStartChat: () => ({ mutate, isPending: false, error: startError }),
  useConversationPhoto: () => null,
}));

import { CustomerAvatar, nameInitial } from "./CustomerAvatar";
import { NewChatDialog } from "./NewChatDialog";

describe("nameInitial", () => {
  it("uses the first letter of a real name and never a phone symbol", () => {
    expect(nameInitial({ contact: { id: "c", name: "kirti", phone: "+919891331696" } } as never)).toBe("K");
    expect(nameInitial({ contact: { id: "c", name: "+919891000010", phone: "+919891000010" } } as never)).toBeNull();
    expect(nameInitial({ contact: null } as never)).toBeNull();
  });

  it("shows a person icon instead of '+' when only a number is known", () => {
    const { container } = render(
      <CustomerAvatar
        conversation={{ id: "c1", connector_type: "waha", contact: { id: "c", name: null, phone: "+919891000010" } } as never}
        className="h-10 w-10"
      />,
    );
    expect(container.textContent).toBe("");
    expect(container.querySelector("svg")).not.toBeNull();
  });
});

describe("NewChatDialog", () => {
  beforeEach(() => {
    mutate.mockReset();
    startError = null;
  });

  it("starts the chat and opens it", () => {
    const onStarted = vi.fn();
    const onClose = vi.fn();
    mutate.mockImplementation((_phone: string, options: { onSuccess: (id: string) => void }) => options.onSuccess("conv-9"));
    render(<NewChatDialog onClose={onClose} onStarted={onStarted} />);

    fireEvent.change(screen.getByLabelText("Mobile number"), { target: { value: "98910 00010" } });
    fireEvent.click(screen.getByRole("button", { name: "Start chat" }));

    expect(mutate).toHaveBeenCalledWith("98910 00010", expect.anything());
    expect(onStarted).toHaveBeenCalledWith("conv-9");
    expect(onClose).toHaveBeenCalled();
  });

  it("explains when the number is not on WhatsApp", () => {
    startError = { detail: "+919100000000 is not on WhatsApp." };
    render(<NewChatDialog onClose={vi.fn()} onStarted={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("not on WhatsApp");
  });

  it("does not submit an empty number", () => {
    render(<NewChatDialog onClose={vi.fn()} onStarted={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Start chat" })).toBeDisabled();
  });
});
