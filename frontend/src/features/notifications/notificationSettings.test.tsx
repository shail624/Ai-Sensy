import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationSettingsPanel } from "@/features/notifications/NotificationSettingsPanel";

const state = vi.hoisted(() => ({
  settings: {
    data: { muted_types: [] as string[] } as { muted_types: string[] } | undefined,
    isPending: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
  save: {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null as unknown,
  },
}));

vi.mock("@/features/notifications/api", () => ({
  useNotificationSettings: () => state.settings,
  useUpdateNotificationSettings: () => state.save,
}));

beforeEach(() => {
  state.settings = {
    data: { muted_types: [] },
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
  state.save = { mutate: vi.fn(), isPending: false, isError: false, error: null };
});

function checkbox(label: string): HTMLInputElement {
  return screen.getByRole("checkbox", { name: label });
}

describe("NotificationSettingsPanel", () => {
  it("renders nothing until it is opened", () => {
    const { container } = render(<NotificationSettingsPanel open={false} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows every category as visible when nothing is muted", () => {
    render(<NotificationSettingsPanel open />);

    expect(checkbox("Follow-up due").checked).toBe(true);
    expect(checkbox("Report ready").checked).toBe(true);
  });

  it("unchecks the categories the server reports as muted", () => {
    // The panel asks "show me", the server stores "hide"; a reversed mapping here would show the
    // operator the exact opposite of their own setting.
    state.settings.data = { muted_types: ["report_ready"] };

    render(<NotificationSettingsPanel open />);

    expect(checkbox("Report ready").checked).toBe(false);
    expect(checkbox("Follow-up due").checked).toBe(true);
  });

  it("saves the category as muted when the operator unchecks it", () => {
    render(<NotificationSettingsPanel open />);

    fireEvent.click(checkbox("Report ready"));

    expect(state.save.mutate).toHaveBeenCalledWith(["report_ready"]);
  });

  it("saves the shorter list when the operator re-checks a muted category", () => {
    state.settings.data = { muted_types: ["case_assigned", "report_ready"] };
    render(<NotificationSettingsPanel open />);

    fireEvent.click(checkbox("Report ready"));

    expect(state.save.mutate).toHaveBeenCalledWith(["case_assigned"]);
  });

  it("keeps the just-toggled box in its new state while the save is in flight", () => {
    // The server still reports the old value until the round trip lands. Adopting it meanwhile
    // would snap the checkbox back under the operator's finger and look like a failed click.
    state.settings.data = { muted_types: [] };
    state.save.isPending = true;

    render(<NotificationSettingsPanel open />);
    fireEvent.click(checkbox("Report ready"));

    expect(checkbox("Report ready").checked).toBe(false);
  });

  it("says plainly that hidden notifications are still recorded", () => {
    render(<NotificationSettingsPanel open />);

    expect(screen.getByText(/still recorded/i)).toBeInTheDocument();
    expect(screen.getByText(/team lead still sees them/i)).toBeInTheDocument();
  });

  it("offers a retry when the settings cannot be read", () => {
    state.settings = {
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("nope"),
      refetch: vi.fn(),
    };

    render(<NotificationSettingsPanel open />);
    fireEvent.click(screen.getByRole("button", { name: /retry|try again/i }));

    expect(state.settings.refetch).toHaveBeenCalled();
  });

  it("surfaces a failed save instead of pretending it worked", () => {
    state.save = {
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: new Error("could not save"),
    };

    render(<NotificationSettingsPanel open />);

    expect(screen.getByRole("alert")).toHaveTextContent(/could not save/i);
  });
});
