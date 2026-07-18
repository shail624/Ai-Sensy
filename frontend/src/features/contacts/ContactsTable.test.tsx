import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ContactsTable } from "@/features/contacts/ContactsTable";
import type { Contact } from "@/features/contacts/types";

function contactFixture(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "c1",
    type: "contact",
    wa_id: "15551234567",
    phone_e164: "+15551234567",
    country_code: null,
    full_name: "Priya Sharma",
    first_name: null,
    last_name: null,
    email: null,
    locale: null,
    profile_name: null,
    opt_in_status: "opted_in",
    opt_in_at: null,
    opt_out_at: null,
    is_active_on_wa: null,
    last_inbound_at: null,
    last_outbound_at: null,
    last_contacted_at: null,
    source: null,
    tags: [],
    attributes: {},
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
    row_version: 0,
    ...overrides,
  };
}

function renderTable(props: Partial<Parameters<typeof ContactsTable>[0]> = {}) {
  return render(
    <MemoryRouter>
      <ContactsTable
        contacts={[contactFixture()]}
        selectedIds={new Set()}
        onToggle={vi.fn()}
        onToggleAll={vi.fn()}
        reactivationKey={null}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("ContactsTable", () => {
  it("renders a row linking to the contact profile", () => {
    renderTable();
    expect(screen.getByRole("link", { name: "Priya Sharma" })).toHaveAttribute(
      "href",
      "/contacts/c1",
    );
    expect(screen.getByText("+15551234567")).toBeInTheDocument();
  });

  it("toggles selection via the row checkbox", () => {
    const onToggle = vi.fn();
    renderTable({ onToggle });
    fireEvent.click(screen.getByRole("checkbox", { name: /select priya/i }));
    expect(onToggle).toHaveBeenCalledWith("c1");
  });

  it("shows a reactivation-status column when a key is provided", () => {
    renderTable({
      contacts: [contactFixture({ attributes: { reactivation_status: "pending" } })],
      reactivationKey: "reactivation_status",
    });
    expect(screen.getByText("Reactivation status")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });
});
