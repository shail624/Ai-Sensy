import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { navItems } from "@/components/layout/navigation";
import { AiFoundationPanel } from "@/features/ai";
import { AutomationBuilder } from "@/features/automation";
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

describe("Phase 3 reactivation and automation foundations", () => {
  it("provides every planned reactivation destination without duplicating a domain engine", () => {
    expect(REACTIVATION_SECTIONS.map((section) => section.key)).toEqual([
      "eligible", "bulk", "interested", "pipeline", "kyc", "documents", "sim", "activation", "completed", "reports",
    ]);
    expect(REACTIVATION_SECTIONS.filter((section) => section.phase === "Connected").map((section) => section.key)).toEqual(["pipeline", "documents", "reports"]);
    expect(REACTIVATION_STAGE_BLUEPRINT).toEqual(["Lead", "Eligibility Check", "Interested", "Documents Received", "Verification", "KYC Approved", "SIM Ordered", "Activation Pending", "Activated", "Completed"]);
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

  it("lets operators design an automation blueprint but never save or run it", () => {
    render(<AutomationBuilder />);
    fireEvent.click(screen.getByRole("button", { name: "Trigger" }));
    fireEvent.click(screen.getByRole("button", { name: "Campaign" }));
    expect(screen.getByText("Approval required")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move Trigger up" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Move Trigger down" }));
    expect(screen.getByRole("button", { name: "Move Trigger down" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move Trigger up" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Save automation" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run test" })).toBeDisabled();
  });

  it("projects typed CRM KYC and SIM values without claiming workflow records", () => {
    const { rerender } = render(<ReactivationSection contact={contact} focus="kyc" />);
    expect(screen.getByText("submitted")).toBeInTheDocument();
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
