import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApprovalCenter } from "@/features/approvals/ApprovalCenter";
import {
  activationToApproval,
  byWaitingLongest,
  kycToApproval,
  type ActivationRecord,
  type KycCase,
  type PendingApproval,
} from "@/features/approvals/types";

/**
 * The Approval Center.
 *
 * CORE-08 was recorded as "Skipped: Not required by product owner", refusing a generic approval
 * *framework* — a second authority deciding who may act. This is deliberately not that: nothing
 * here decides anything, each item is approved through the endpoint its own module already owns,
 * and the screen only answers the question neither module could — what is waiting on me.
 */

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  items: [] as import("@/features/approvals/types").PendingApproval[],
  approved: [] as { id: string; source: string; version: number }[],
  fails: false,
}));

vi.mock("@/features/approvals/api", () => ({
  apiErrorMessage: (error: unknown) => String((error as Error)?.message ?? error),
  useHasPermission: (code: string) => state.permissions.includes(code),
  usePendingApprovals: () => ({
    data: state.items,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useApprove: () => ({
    mutateAsync: async (item: { id: string; source: string; rowVersion: number }) => {
      if (state.fails) throw new Error("Somebody else decided this one.");
      state.approved.push({ id: item.id, source: item.source, version: item.rowVersion });
    },
    isPending: false,
    isError: state.fails,
    error: state.fails ? new Error("Somebody else decided this one.") : null,
  }),
}));

function withProviders(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const kycItem: PendingApproval = {
  id: "k1",
  source: "kyc",
  label: "KYC verification",
  detail: "holder verified · Delhi presence unverified",
  contactId: "c1",
  rowVersion: 4,
  waitingSince: "2026-09-10T00:00:00Z",
};

const activationItem: PendingApproval = {
  id: "a1",
  source: "activation",
  label: "ACT-5521",
  detail: "Ready for activation approval",
  contactId: "c2",
  rowVersion: 2,
  waitingSince: "2026-09-15T00:00:00Z",
};

beforeEach(() => {
  state.permissions = ["kyc:read", "kyc:approve", "activation:read", "activation:approve"];
  state.items = [kycItem, activationItem];
  state.approved = [];
  state.fails = false;
});

describe("what is waiting on me", () => {
  it("gathers both modules' work onto one screen", () => {
    // Until now this lived in two separate workspaces, and something waiting in the one nobody
    // opened today waited another day.
    withProviders(<ApprovalCenter />);

    expect(screen.getByText("KYC verification")).toBeInTheDocument();
    expect(screen.getByText("ACT-5521")).toBeInTheDocument();
  });

  it("approves through the module that owns the decision, with the version seen", async () => {
    withProviders(<ApprovalCenter />);

    fireEvent.click(screen.getAllByRole("button", { name: "Approve" })[0]!);

    await waitFor(() =>
      expect(state.approved).toEqual([{ id: "k1", source: "kyc", version: 4 }]),
    );
  });

  it("shows the queue but no button to somebody who may read and not sign off", () => {
    // A button they cannot use is worse than no button: it promises an authority they lack.
    state.permissions = ["kyc:read", "activation:read"];

    withProviders(<ApprovalCenter />);

    expect(screen.getByText("KYC verification")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("offers the approve button only for the source the user may approve", () => {
    state.permissions = ["kyc:read", "activation:read", "activation:approve"];

    withProviders(<ApprovalCenter />);

    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(1);
  });

  it("says out loud when an approval is refused", async () => {
    state.fails = true;
    withProviders(<ApprovalCenter />);

    fireEvent.click(screen.getAllByRole("button", { name: "Approve" })[0]!);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/Somebody else decided/i),
    );
  });

  it("tells an empty queue apart from no access", () => {
    state.items = [];
    withProviders(<ApprovalCenter />);
    expect(screen.getByText(/asking for a decision right now/i)).toBeInTheDocument();

    state.permissions = [];
    withProviders(<ApprovalCenter />);
    expect(screen.getByText(/need KYC or activation read permission/i)).toBeInTheDocument();
  });
});

describe("the shape of the queue", () => {
  it("puts what has waited longest first", () => {
    // The thing that has been waiting longest is the thing most worth deciding.
    const sorted = [activationItem, kycItem].sort(byWaitingLongest);
    expect(sorted.map((item) => item.id)).toEqual(["k1", "a1"]);
  });

  it("reads each record in its own module's words", () => {
    const kyc = kycToApproval({
      id: "k9",
      contact_id: "c9",
      row_version: 1,
      created_at: "2026-09-01T00:00:00Z",
      holder_verified: false,
      delhi_presence_verified: true,
    } as unknown as KycCase);
    expect(kyc.detail).toContain("holder unverified");
    expect(kyc.detail).toContain("Delhi presence verified");

    const activation = activationToApproval({
      id: "a9",
      contact_id: "c9",
      row_version: 1,
      created_at: "2026-09-01T00:00:00Z",
      approval_reference: null,
    } as unknown as ActivationRecord);
    // No reference is a real state, and "Activation record" is more honest than an empty row.
    expect(activation.label).toBe("Activation record");
  });
});
