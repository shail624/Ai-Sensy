import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ReactivationOverview,
  ReactivationPage,
  ReactivationWorkspace,
} from "@/pages/ReactivationPage";

const mocks = vi.hoisted(() => ({
  permissions: {
    value: ["reactivation:read", "kyc:read", "documents:read", "analytics:read"],
  },
}));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (code: string) => mocks.permissions.value.includes(code),
}));

vi.mock("@/features/kyc", () => ({
  KycOperationsWorkspace: () => <div>KYC workspace</div>,
}));

vi.mock("@/features/reactivation", async () => {
  const actual = await vi.importActual<typeof import("@/features/reactivation")>(
    "@/features/reactivation",
  );
  return {
    ...actual,
    DocumentCenter: () => <div>Document workspace</div>,
    ReactivationPipelineBoard: () => <div>Pipeline workspace</div>,
    ReactivationReports: () => <div>Reports workspace</div>,
  };
});

function LocationProbe(): JSX.Element {
  const location = useLocation();
  return <div data-testid="location">{`${location.pathname}${location.search}`}</div>;
}

function renderRoute(initialEntry: string): void {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/reactivation" element={<ReactivationPage />}>
          <Route index element={<ReactivationOverview />} />
          <Route path="pipeline" element={<ReactivationWorkspace />} />
          <Route path="kyc" element={<ReactivationWorkspace />} />
          <Route path="documents" element={<ReactivationWorkspace />} />
          <Route path="reports" element={<ReactivationWorkspace />} />
          <Route path="eligible" element={<ReactivationWorkspace />} />
          <Route path="bulk-eligibility" element={<ReactivationWorkspace />} />
          <Route path="interested" element={<ReactivationWorkspace />} />
          <Route path="sim-orders" element={<ReactivationWorkspace />} />
          <Route path="activation" element={<ReactivationWorkspace />} />
          <Route path="completed" element={<ReactivationWorkspace />} />
        </Route>
        <Route path="/contacts" element={<div>Contacts import workflow</div>} />
      </Routes>
      <LocationProbe />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mocks.permissions.value = [
    "reactivation:read",
    "kyc:read",
    "documents:read",
    "analytics:read",
  ];
});

describe("Reactivation operational hierarchy", () => {
  it("makes the real CRM the default Reactivation destination", () => {
    renderRoute("/reactivation");
    expect(screen.getByText("Pipeline workspace")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/reactivation/pipeline");
  });

  it("shows only connected sections permitted by the existing RBAC authority", () => {
    // Neither sim:read nor activation:read, so neither fulfilment link may appear.
    mocks.permissions.value = ["reactivation:read", "documents:read"];
    renderRoute("/reactivation/pipeline");
    expect(screen.getByRole("link", { name: "Pipeline" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Documents" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "KYC" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /SIM orders/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Activation" })).not.toBeInTheDocument();
  });

  it("opens the fulfilment queues rather than a filtered case list", () => {
    // These two links used to redirect to the pipeline filtered by stage, which showed *cases* at
    // the SIM stage and not the orders themselves -- no serial, no address, no dispatch state. The
    // scope document said no standalone fulfilment workspace would be built; the owner asked for
    // one (SIM-01), and these links now reach it.
    renderRoute("/reactivation/sim-orders");
    expect(screen.getByText("Fulfilment queues")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/reactivation/sim-orders");
  });

  it("reaches the same queues from the activation link", () => {
    // One component for both: "what is waiting on us" is one question, and two screens would make
    // an operator check twice to answer it once.
    renderRoute("/reactivation/activation");
    expect(screen.getByText("Fulfilment queues")).toBeInTheDocument();
  });

  it("redirects bulk eligibility to the existing governed import workflow", () => {
    renderRoute("/reactivation/bulk-eligibility");
    expect(screen.getByTestId("location")).toHaveTextContent("/contacts?import=1");
  });
});
