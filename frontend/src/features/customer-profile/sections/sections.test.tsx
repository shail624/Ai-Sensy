import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssignmentSection } from "@/features/customer-profile/sections/AssignmentSection";
import { ConversationHistorySection } from "@/features/customer-profile/sections/ConversationHistorySection";
import { CustomAttributesSection } from "@/features/customer-profile/sections/CustomAttributesSection";
import { IdentitySection } from "@/features/customer-profile/sections/IdentitySection";
import { NotesSection } from "@/features/customer-profile/sections/NotesSection";
import type { AttributeDefinition, Contact, Note } from "@/features/customer-profile/types";

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

function attrDef(overrides: Partial<AttributeDefinition> = {}): AttributeDefinition {
  return {
    id: "a1",
    type: "attribute",
    key_name: "vi_number",
    label: "Vi Number",
    data_type: "string",
    enum_values: null,
    is_indexed: false,
    is_pii: false,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
    ...overrides,
  };
}

describe("customer profile sections", () => {
  it("IdentitySection shows name, phone and WhatsApp number", () => {
    render(<IdentitySection contact={contactFixture()} />);
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
    expect(screen.getByText("+15551234567")).toBeInTheDocument();
    expect(screen.getByText("15551234567")).toBeInTheDocument();
  });

  it("CustomAttributesSection renders defined attributes with their labels", () => {
    const contact = contactFixture({ attributes: { vi_number: "9876543210" } });
    render(<CustomAttributesSection contact={contact} definitions={[attrDef()]} />);
    expect(screen.getByText("Vi Number")).toBeInTheDocument();
    expect(screen.getByText("9876543210")).toBeInTheDocument();
  });

  it("CustomAttributesSection shows an empty state when nothing is set", () => {
    render(<CustomAttributesSection contact={contactFixture()} definitions={[attrDef()]} />);
    expect(screen.getByText(/no custom attributes set/i)).toBeInTheDocument();
  });

  it("ConversationHistorySection reports it is unavailable from a contact", () => {
    render(<ConversationHistorySection />);
    expect(screen.getByText(/not available from a contact/i)).toBeInTheDocument();
  });

  it("AssignmentSection shows the agent when provided and an empty state otherwise", () => {
    const { rerender } = render(<AssignmentSection assignedAgent="agent-1" />);
    expect(screen.getByText(/agent-1/)).toBeInTheDocument();
    rerender(<AssignmentSection />);
    expect(screen.getByText(/no assignment/i)).toBeInTheDocument();
  });

  it("NotesSection renders provided notes", () => {
    const notes: Note[] = [
      { id: "n1", author: "Asha", body: "Called back", created_at: "2026-07-18T00:00:00Z" },
    ];
    render(<NotesSection notes={notes} />);
    expect(screen.getByText("Called back")).toBeInTheDocument();
  });
});
