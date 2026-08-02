import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { navItems } from "@/components/layout/navigation";
import { AiFoundationPanel } from "@/features/ai";
import { ReactivationSection } from "@/features/customer-profile/sections/ReactivationSection";
import type { Contact } from "@/features/customer-profile/types";
import { REACTIVATION_SECTIONS, REACTIVATION_STAGE_BLUEPRINT } from "@/features/reactivation";
import { ScanWorkspace } from "@/features/scan";

const contact = {
  id: "contact-1", type: "contact", wa_id: "919900000001", phone_e164: "+919900000001", country_code: "IN",
  full_name: "Asha", first_name: null, last_name: null, email: null, locale: null, profile_name: null,
  opt_in_status: "opted_in", opt_in_at: null, opt_out_at: null, is_active_on_wa: true,
  last_inbound_at: null, last_outbound_at: null, last_contacted_at: null, source: "import", tags: [],
  attributes: { kyc_status: "submitted", sim_status: "ordered" }, created_at: "2026-07-25T00:00:00Z",
  updated_at: "2026-07-25T00:00:00Z", row_version: 1,
} satisfies Contact;

vi.mock("@/lib/auth", () => ({ useHasPermission: () => true }));
vi.mock("@/features/kyc/api", () => ({
  apiErrorMessage: () => "KYC unavailable",
  useContactKycCases: () => ({
    data: [{
      id: "kyc-1", contact_id: "contact-1", reactivation_case_id: "case-1",
      requester_user_id: "user-1", status: "under_review", owner_user_id: "user-2",
      holder_verified: true, delhi_presence_verified: true,
      active_delhi_number_verified: false, appointment_at: null, row_version: 3,
      created_at: "2026-08-01T00:00:00Z", updated_at: "2026-08-02T00:00:00Z",
    }],
    isLoading: false, isError: false, error: null, refetch: vi.fn(),
  }),
}));

describe("Phase 3 reactivation and automation foundations", () => {
  it("provides every planned reactivation destination without duplicating a domain engine", () => {
    expect(REACTIVATION_SECTIONS.map((section) => section.key)).toEqual([
      "eligible", "bulk", "interested", "pipeline", "kyc", "documents", "sim", "activation", "completed", "reports",
    ]);
    expect(REACTIVATION_SECTIONS.filter((section) => section.phase === "Connected").map((section) => section.key)).toEqual(["pipeline", "kyc", "documents", "reports"]);
    expect(REACTIVATION_STAGE_BLUEPRINT).toEqual([
      "New lead", "Follow-up", "Interested", "Eligibility check", "Eligible",
      "Documents pending", "Documents received", "KYC pending", "Verification", "Confirmed",
      "SIM order", "Activation pending", "Completed", "Not eligible", "Not interested",
    ]);
    expect(navItems.find((item) => item.path === "/reactivation")?.permission).toBe("reactivation:read");
  });

  it("keeps Scan Studio separate from the official WhatsApp module and permission-gated", () => {
    const scan = navItems.find((item) => item.path === "/scan");
    const whatsapp = navItems.find((item) => item.path === "/channels");
    expect(scan?.permission).toBe("contacts:read");
    expect(scan?.path).not.toBe(whatsapp?.path);
    render(<MemoryRouter><ScanWorkspace /></MemoryRouter>);
    expect(screen.getByText("Architecture boundary enforced")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload scan batch" })).toBeDisabled();
  });

  it("projects governed KYC records while retaining the honest SIM foundation", () => {
    const { rerender } = render(<ReactivationSection contact={contact} focus="kyc" />);
    expect(screen.getByText("Under review")).toBeInTheDocument();
    expect(screen.getByText("Active Delhi number")).toBeInTheDocument();
    expect(screen.queryByText("ordered")).not.toBeInTheDocument();
    rerender(<ReactivationSection contact={contact} focus="sim" />);
    expect(screen.getByText("ordered")).toBeInTheDocument();
  });

  it("adds document summarization as a human-controlled AI seam", () => {
    render(<AiFoundationPanel capabilities={["document"]} context="governed customer documents" />);
    expect(screen.getByRole("heading", { name: "Document summary" })).toBeInTheDocument();
    expect(screen.getByText("Nothing is generated or sent automatically")).toBeInTheDocument();
  });
});
