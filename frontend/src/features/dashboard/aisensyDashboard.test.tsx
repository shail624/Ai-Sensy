import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { InfoTooltip } from "@/components/ui";

import { summarizeAccount } from "@/features/channels/accountSummary";
import type { PhoneNumber, Waba } from "@/features/channels/types";

const mutate = vi.fn();
vi.mock("@/features/channels/api", () => ({
  useUpdateBusinessProfile: () => ({ mutate, isPending: false, isError: false, error: null }),
}));

import { EditBusinessProfileDialog } from "./EditBusinessProfileDialog";
import { SetupChecklist, buildSetupSteps } from "./SetupChecklist";

const waba = (overrides: Partial<Waba> = {}): Waba =>
  ({ id: "w1", business_name: "Vi Team", status: "active", ...overrides }) as Waba;
const number = (overrides: Partial<PhoneNumber> = {}): PhoneNumber =>
  ({ id: "n1", waba_id: "w1", display_number: "+91 99903 29329", status: "connected", is_default: false, quality_rating: "GREEN", messaging_tier: "TIER_1K", ...overrides }) as PhoneNumber;

describe("summarizeAccount", () => {
  it("is not connected without an account", () => {
    expect(summarizeAccount([], []).status).toBe("not_connected");
  });

  it("is pending until a number is connected", () => {
    expect(summarizeAccount([waba()], [number({ status: "PENDING" })]).status).toBe("pending");
  });

  it("is live with an active account and connected number, preferring the default number", () => {
    const summary = summarizeAccount([waba()], [number(), number({ id: "n2", is_default: true })]);
    expect(summary.status).toBe("live");
    expect(summary.number?.id).toBe("n2");
    expect(summary.businessName).toBe("Vi Team");
  });
});

describe("SetupChecklist", () => {
  const facts = { whatsappConnected: true, templateApproved: false, hasContacts: false, hasCampaign: false };

  it("counts remaining steps and opens the NEXT step with its real action", () => {
    render(<MemoryRouter><SetupChecklist steps={buildSetupSteps(facts)} /></MemoryRouter>);
    expect(screen.getByText("3 steps left")).toBeInTheDocument();
    expect(screen.getByText("NEXT")).toBeInTheDocument();
    const [nextToggle] = screen.getAllByRole("button", { name: /get a template approved/i });
    expect(nextToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("link", { name: "Create Template" })[0]).toHaveAttribute("href", "/templates/new");
  });

  it("toggles a step accordion and the All Steps list", () => {
    render(<MemoryRouter><SetupChecklist steps={buildSetupSteps(facts)} /></MemoryRouter>);
    const [nextToggle] = screen.getAllByRole("button", { name: /get a template approved/i });
    fireEvent.click(nextToggle!);
    expect(nextToggle).toHaveAttribute("aria-expanded", "false");

    const all = screen.getByRole("button", { name: /all steps/i });
    fireEvent.click(all);
    expect(all).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: /show less/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect whatsapp business account \(completed\)/i })).toBeInTheDocument();
  });

  it("reports completion when every step is done", () => {
    const done = { whatsappConnected: true, templateApproved: true, hasContacts: true, hasCampaign: true };
    render(<MemoryRouter><SetupChecklist steps={buildSetupSteps(done)} /></MemoryRouter>);
    expect(screen.getByText("All done")).toBeInTheDocument();
    expect(screen.queryByText("NEXT")).not.toBeInTheDocument();
  });
});

describe("InfoTooltip", () => {
  it("shows its lines on hover and focus, and hides on leave", () => {
    render(<InfoTooltip label="About Quality Rating" lines={["High quality."]} />);
    const trigger = screen.getByRole("button", { name: "About Quality Rating" });
    const tip = screen.getByRole("tooltip", { hidden: true });
    expect(tip).toHaveClass("invisible");
    fireEvent.mouseEnter(trigger);
    expect(tip).not.toHaveClass("invisible");
    expect(trigger).toHaveAttribute("aria-describedby", tip.id);
    fireEvent.mouseLeave(trigger);
    expect(tip).toHaveClass("invisible");
    fireEvent.focus(trigger);
    expect(tip).toHaveTextContent("• High quality.");
  });
});

describe("EditBusinessProfileDialog", () => {
  const profile = { about: null, address: "Old", description: "Desc", email: "a@vi.co", websites: ["https://vi.in"], vertical: "OTHER", profile_picture_url: null };

  it("sends only the fields the operator changed", () => {
    const onClose = vi.fn();
    render(<EditBusinessProfileDialog numberId="n1" profile={profile} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText("Address"), { target: { value: "New" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(mutate).toHaveBeenCalledWith({ numberId: "n1", body: { address: "New" } }, { onSuccess: onClose });
  });

  it("closes without calling Meta when nothing changed", () => {
    mutate.mockClear();
    const onClose = vi.fn();
    render(<EditBusinessProfileDialog numberId="n1" profile={profile} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClose).toHaveBeenCalled();
    expect(mutate).not.toHaveBeenCalled();
  });
});
