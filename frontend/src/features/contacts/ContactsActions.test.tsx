import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ContactsActions } from "@/features/contacts/ContactsActions";

const permission = { allowed: true };

vi.mock("@/lib/auth", () => ({
  useHasPermission: () => permission.allowed,
}));

vi.mock("@/features/contacts/BulkActionDialog", () => ({
  BulkActionDialog: ({ mode, ids }: { mode: string; ids: string[] }) => (
    <div role="dialog" aria-label="Export contacts">{mode}:{ids.length}</div>
  ),
}));

function renderActions(): void {
  render(
    <MemoryRouter>
      <ContactsActions rules={[]} />
    </MemoryRouter>,
  );
}

describe("ContactsActions", () => {
  it("opens a compact current-view actions menu", () => {
    permission.allowed = true;
    renderActions();
    const trigger = screen.getByRole("button", { name: "Actions" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);

    const menu = screen.getByRole("menu", { name: "Contact actions" });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(within(menu).getByRole("menuitem", { name: "Export history" })).toHaveAttribute(
      "href",
      "/downloads",
    );
  });

  it("exports the complete filtered view without inventing a selection", () => {
    permission.allowed = true;
    renderActions();
    fireEvent.click(screen.getByRole("button", { name: "Actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Export current view" }));
    expect(screen.getByRole("dialog", { name: "Export contacts" })).toHaveTextContent("export:0");
  });

  it("is absent without export permission", () => {
    permission.allowed = false;
    renderActions();
    expect(screen.queryByRole("button", { name: "Actions" })).not.toBeInTheDocument();
  });
});
