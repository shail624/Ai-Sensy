import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContactsTable } from "@/features/contacts/ContactsTable";
import type { Contact } from "@/features/contacts/types";

/** Force the compact (phone) branch: only `max-width` queries match. */
function useCompactViewport(): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("max-width"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

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

describe("ContactsTable — compact (below md)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("reflows to stacked cards instead of a table", () => {
    useCompactViewport();
    renderTable();

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Priya Sharma" })).toHaveAttribute("href", "/contacts/c1");
    expect(screen.getByText("+15551234567")).toBeInTheDocument();
    expect(screen.getByText("Opted in")).toBeInTheDocument();
  });

  it("keeps a per-card checkbox and the select-all control", () => {
    useCompactViewport();
    const onToggle = vi.fn();
    const onToggleAll = vi.fn();
    renderTable({ onToggle, onToggleAll });

    fireEvent.click(screen.getByRole("checkbox", { name: /select priya/i }));
    expect(onToggle).toHaveBeenCalledWith("c1");

    fireEvent.click(screen.getByRole("checkbox", { name: /select all contacts/i }));
    expect(onToggleAll).toHaveBeenCalled();
  });

  it("selects a card on long press", () => {
    useCompactViewport();
    vi.useFakeTimers();
    const onToggle = vi.fn();
    renderTable({ onToggle });

    const card = screen.getAllByRole("listitem")[0]!;
    fireEvent.pointerDown(card, { pointerType: "touch", clientX: 10, clientY: 10 });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(onToggle).toHaveBeenCalledWith("c1");
  });

  it("cancels the long press when the finger scrolls away", () => {
    useCompactViewport();
    vi.useFakeTimers();
    const onToggle = vi.fn();
    renderTable({ onToggle });

    const card = screen.getAllByRole("listitem")[0]!;
    fireEvent.pointerDown(card, { pointerType: "touch", clientX: 10, clientY: 10 });
    fireEvent.pointerMove(card, { pointerType: "touch", clientX: 10, clientY: 90 });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(onToggle).not.toHaveBeenCalled();
  });

  it("tapping a card toggles selection once a selection is active", () => {
    useCompactViewport();
    const onToggle = vi.fn();
    renderTable({ onToggle, selectedIds: new Set(["c9"]) });

    fireEvent.click(screen.getAllByRole("listitem")[0]!);
    expect(onToggle).toHaveBeenCalledWith("c1");
  });

  it("carries the reactivation status onto the card", () => {
    useCompactViewport();
    renderTable({
      contacts: [contactFixture({ attributes: { reactivation_status: "pending" } })],
      reactivationKey: "reactivation_status",
    });
    expect(screen.getByText("Reactivation status")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });
});
