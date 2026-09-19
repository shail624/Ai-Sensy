import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChannelHealthStrip } from "@/features/dashboard/ChannelHealthStrip";

const state = vi.hoisted(() => ({
  numbers: {
    data: [] as unknown[],
    isPending: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
}));

vi.mock("@/features/channels/api", () => ({ useNumbers: () => state.numbers }));

function number(overrides: Record<string, unknown> = {}) {
  return {
    id: "n1",
    display_number: "+919990000001",
    status: "connected",
    quality_rating: "GREEN",
    messaging_tier: "TIER_10K",
    throughput_level: "STANDARD",
    mps_limit: 80,
    last_synced_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderStrip() {
  return render(
    <MemoryRouter>
      <ChannelHealthStrip />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  state.numbers = {
    data: [number()],
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
});

describe("ChannelHealthStrip", () => {
  it("shows the number, its standing and what its tier permits", () => {
    renderStrip();

    expect(screen.getByText("+919990000001")).toBeInTheDocument();
    expect(screen.getByText("Good standing")).toBeInTheDocument();
    // The tier's enum name hides the only part an operator needs before scheduling a send.
    expect(screen.getByText("10,000 customers / 24h")).toBeInTheDocument();
  });

  it("says when the figures were last checked", () => {
    // These are what the last sync wrote, not a live call to Meta. A green badge with no timestamp
    // reads as "fine now" when it may mean "fine on Tuesday".
    state.numbers.data = [number({ last_synced_at: new Date(Date.now() - 3 * 3600_000).toISOString() })];

    renderStrip();

    expect(screen.getByText(/checked 3h ago/)).toBeInTheDocument();
  });

  it("admits when a number has never been checked", () => {
    state.numbers.data = [number({ last_synced_at: null })];

    renderStrip();

    expect(screen.getByText(/never checked/)).toBeInTheDocument();
  });

  it("flags a number Meta has marked red", () => {
    state.numbers.data = [number({ quality_rating: "RED" })];

    renderStrip();

    expect(screen.getByText("Quality flagged")).toBeInTheDocument();
  });

  it("treats a disconnected number as worse than any quality rating", () => {
    state.numbers.data = [number({ status: "disconnected", quality_rating: "GREEN" })];

    renderStrip();

    expect(screen.getByText("disconnected")).toBeInTheDocument();
    expect(screen.queryByText("Good standing")).not.toBeInTheDocument();
  });

  it("puts the number that will stop a send first", () => {
    // On an account with several numbers the healthy ones would otherwise push the broken one off
    // the end of the row, which is the one case the strip exists for.
    state.numbers.data = [
      number({ id: "n1", display_number: "+919990000001", quality_rating: "GREEN" }),
      number({ id: "n2", display_number: "+919990000002", quality_rating: "RED" }),
      number({ id: "n3", display_number: "+919990000003", quality_rating: "YELLOW" }),
    ];

    renderStrip();

    const listed = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(listed.map((item) => item.textContent?.slice(0, 13))).toEqual([
      "+919990000002",
      "+919990000003",
      "+919990000001",
    ]);
  });

  it("says nothing can be sent when no number is connected", () => {
    state.numbers.data = [];

    renderStrip();

    expect(screen.getByText(/nothing can be sent/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Connect a number/i })).toBeInTheDocument();
  });

  it("does not present a failed lookup as healthy silence", () => {
    state.numbers = {
      data: [],
      isPending: false,
      isError: true,
      error: new Error("channel service is down"),
      refetch: vi.fn(),
    };

    renderStrip();

    expect(screen.getByRole("alert")).toHaveTextContent(/unavailable/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/channel service is down/i);
  });
});
