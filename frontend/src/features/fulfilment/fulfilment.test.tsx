import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FulfilmentQueues } from "@/features/fulfilment/FulfilmentQueues";

/**
 * The SIM and activation queues.
 *
 * Both lifecycles have had complete APIs since CORE-02 and no screen at all: the nav links
 * resolved to the reactivation pipeline filtered by stage, which shows *cases* at the SIM stage
 * and not the orders — no serial, no address, no dispatch state. "What is waiting on us today"
 * had no answer anywhere, which is the question a queue exists to answer.
 */

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  orders: [] as Record<string, unknown>[],
  records: [] as Record<string, unknown>[],
  moved: [] as { id: string; to: string; version: number }[],
  fails: false,
}));

vi.mock("@/features/fulfilment/api", () => ({
  apiErrorMessage: (error: unknown) => String((error as Error)?.message ?? error),
  useHasPermission: (code: string) => state.permissions.includes(code),
  useSimOrders: () => ({
    data: state.orders,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useActivationRecords: () => ({
    data: state.records,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useTransitionSimOrder: () => ({
    // Shaped like `useMutation`'s result: `mutate` starts the work and never hands back a promise,
    // so a refused move lands in `isError` instead of escaping as an unhandled rejection.
    mutate: ({ order, to }: { order: { id: string; row_version: number }; to: string }) => {
      if (state.fails) return;
      state.moved.push({ id: order.id, to, version: order.row_version });
    },
    isPending: false,
    isError: state.fails,
    error: state.fails ? new Error("That order moved while you were looking at it.") : null,
  }),
  useTransitionActivation: () => ({
    mutate: ({ record, to }: { record: { id: string; row_version: number }; to: string }) => {
      state.moved.push({ id: record.id, to, version: record.row_version });
    },
    isPending: false,
    isError: false,
    error: null,
  }),
}));

function order(overrides: Record<string, unknown> = {}) {
  return {
    id: "so1",
    status: "assigned",
    sim_serial: "89911000012345",
    delivery_address: "12 MG Road, Delhi",
    service_area: "Delhi NCR",
    failure_reason: null,
    row_version: 3,
    updated_at: "2026-09-16T10:00:00Z",
    ...overrides,
  };
}

function record(overrides: Record<string, unknown> = {}) {
  return {
    id: "ar1",
    status: "verification",
    approval_reference: "ACT-5521",
    rejection_reason: null,
    row_version: 2,
    updated_at: "2026-09-16T10:00:00Z",
    ...overrides,
  };
}

function withProviders(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  state.permissions = ["sim:read", "sim:write", "activation:read", "activation:write"];
  state.orders = [order()];
  state.records = [record()];
  state.moved = [];
  state.fails = false;
});

describe("fulfilment queues", () => {
  it("shows the order itself, not the case it belongs to", () => {
    // The serial and the address are the whole reason this screen exists: the filtered case list
    // it replaced could show neither.
    withProviders(<FulfilmentQueues />);

    expect(screen.getByText("89911000012345")).toBeInTheDocument();
    expect(screen.getByText("12 MG Road, Delhi")).toBeInTheDocument();
    expect(screen.getByText("Delhi NCR")).toBeInTheDocument();
  });

  it("hides settled work until it is asked for", () => {
    // A queue that keeps showing delivered orders stops being a list of what to do and becomes a
    // list of what happened.
    state.orders = [order(), order({ id: "so2", sim_serial: "DONE-1", status: "delivered" })];

    withProviders(<FulfilmentQueues />);
    expect(screen.queryByText("DONE-1")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Show settled/ }));
    expect(screen.getByText("DONE-1")).toBeInTheDocument();
  });

  it("sends the row version the operator actually looked at", async () => {
    // Two people work one queue. The second must be told the order moved, not silently overwrite
    // the first, and the server can only tell them if it is given the version they saw.
    withProviders(<FulfilmentQueues />);

    fireEvent.click(screen.getByRole("button", { name: "Dispatched" }));

    await waitFor(() => expect(state.moved).toEqual([{ id: "so1", to: "dispatched", version: 3 }]));
  });

  it("offers only the moves that make sense from where the order is", () => {
    // The API enforces the real rules; this only decides which buttons are worth drawing, so
    // nobody is offered "requested" on something already on a van.
    withProviders(<FulfilmentQueues />);

    expect(screen.getByRole("button", { name: "Dispatched" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Failed" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Requested" })).not.toBeInTheDocument();
  });

  it("says out loud when a move is refused", async () => {
    state.fails = true;
    withProviders(<FulfilmentQueues />);

    fireEvent.click(screen.getByRole("button", { name: "Dispatched" }));

    await waitFor(() =>
      expect(screen.getAllByRole("alert")[0]).toHaveTextContent(/moved while you were looking/i),
    );
  });

  it("offers no buttons to somebody who may only read", () => {
    state.permissions = ["sim:read", "activation:read"];

    withProviders(<FulfilmentQueues />);

    expect(screen.getByText("89911000012345")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Dispatched" })).not.toBeInTheDocument();
  });

  it("shows only the queue a reader is allowed to see", () => {
    state.permissions = ["sim:read"];

    withProviders(<FulfilmentQueues />);

    expect(screen.getByText("SIM delivery")).toBeInTheDocument();
    expect(screen.queryByText("Activation")).not.toBeInTheDocument();
  });

  it("searches by serial, address or area rather than by id", () => {
    // An operator holds a serial off a physical SIM or an address off a phone call; nobody holds
    // a UUID.
    state.orders = [order(), order({ id: "so2", sim_serial: "OTHER-9", service_area: "Mumbai" })];

    withProviders(<FulfilmentQueues />);
    fireEvent.change(screen.getByLabelText("Search by serial, address or area"), {
      target: { value: "mumbai" },
    });

    expect(screen.getByText("OTHER-9")).toBeInTheDocument();
    expect(screen.queryByText("89911000012345")).not.toBeInTheDocument();
  });

  it("counts each column, so a backlog is visible without counting rows", () => {
    state.orders = [order(), order({ id: "so2", sim_serial: "B" }), order({ id: "so3", sim_serial: "C" })];

    withProviders(<FulfilmentQueues />);

    const column = screen.getByRole("region", { name: /Assigned/ });
    expect(within(column).getByText("3")).toBeInTheDocument();
  });

  it("tells an empty queue apart from a filtered one", () => {
    state.orders = [];
    state.records = [];

    withProviders(<FulfilmentQueues />);

    expect(screen.getAllByText(/Nothing waiting/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/reached the customer or been closed/).length).toBe(1);
  });
});
