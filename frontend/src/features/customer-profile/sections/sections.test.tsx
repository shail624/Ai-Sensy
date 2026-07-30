import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { CustomerProfile } from "@/features/customer-profile";

import { AssignmentSection } from "@/features/customer-profile/sections/AssignmentSection";
import { ConversationHistorySection } from "@/features/customer-profile/sections/ConversationHistorySection";
import { CustomAttributesSection } from "@/features/customer-profile/sections/CustomAttributesSection";
import { IdentitySection } from "@/features/customer-profile/sections/IdentitySection";
import { NotesSection } from "@/features/customer-profile/sections/NotesSection";
import type { AttributeDefinition, Contact, Note } from "@/features/customer-profile/types";

/** Responses the mocked client serves, swapped per test. */
const apiResponses: { value: Record<string, unknown> } = { value: {} };

vi.mock("@/lib/api/client", () => {
  const GET = async (path: string) =>
    path in apiResponses.value
      ? { data: apiResponses.value[path] }
      : { error: new Error(`no stub for ${path}`) };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

vi.mock("@/lib/auth", () => ({
  useHasPermission: () => true,
  useAuth: () => ({ hasPermission: () => true }),
}));

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

// --- Profile header ------------------------------------------------------------------------------

describe("CustomerProfile header", () => {
  const responses: Record<string, unknown> = {};

  function withProviders(ui: React.ReactElement) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("leads with the identity and the opt-in standing", async () => {
    responses["/api/v1/contacts/{contact_id}"] = contactFixture();
    responses["/api/v1/custom-attributes"] = [];
    apiResponses.value = responses;

    withProviders(<CustomerProfile contactId="c1" />);

    expect(await screen.findByRole("heading", { name: "Priya Sharma" })).toBeInTheDocument();
    expect(screen.getAllByText("+15551234567").length).toBeGreaterThan(0);
    expect(screen.getByText("Opted in")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Payments" })).not.toBeInTheDocument();
  });

  it("renders an unknown opt-in value verbatim rather than guessing", async () => {
    apiResponses.value = {
      "/api/v1/contacts/{contact_id}": contactFixture({ opt_in_status: "revoked" }),
      "/api/v1/custom-attributes": [],
    };

    withProviders(<CustomerProfile contactId="c1" />);

    // Both the header pill and the identity section show it, neither translates it.
    expect((await screen.findAllByText("revoked")).length).toBeGreaterThan(0);
  });
});
