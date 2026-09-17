import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReachabilityPanel } from "@/features/scan/ReachabilityPanel";

const state = vi.hoisted(() => ({
  asked: [] as { verdict: string; q: string }[],
  countsAsked: [] as string[],
  counts: { data: undefined as unknown, isPending: false },
  result: {
    data: undefined as unknown,
    isPending: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
}));

vi.mock("@/features/scan/api", () => ({
  useReachability: (verdict: string, q: string) => {
    state.asked.push({ verdict, q });
    return state.result;
  },
  useReachabilityCounts: (q: string) => {
    state.countsAsked.push(q);
    return state.counts;
  },
}));

function page(rows: unknown[], hasMore = false) {
  return { data: rows, page: { limit: 50, has_more: hasMore, next_cursor: null } };
}

const reached = {
  contact_id: "11111111-1111-4111-8111-111111111111",
  full_name: "Asha Mehta",
  phone_e164: "+919990000001",
  verdict: "reachable",
  last_delivered_at: "2026-09-01T10:00:00Z",
  last_undeliverable_at: null,
};

beforeEach(() => {
  state.asked = [];
  state.countsAsked = [];
  state.counts = { data: { reachable: 1, unreachable: 1, unknown: 1 }, isPending: false };
  state.result = {
    data: page([reached]),
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
});

describe("ReachabilityPanel", () => {
  it("tallies the three verdicts", () => {
    state.counts.data = { reachable: 120, unreachable: 7, unknown: 4300 };

    render(<ReachabilityPanel />);

    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("4,300")).toBeInTheDocument();
  });

  it("says that 'never messaged' means untested, not a soft no", () => {
    // The distinction decides the next action: a campaign, not a cleanup.
    render(<ReachabilityPanel />);

    expect(screen.getByText(/No campaign has ever included these numbers/i)).toBeInTheDocument();
  });

  it("shows the dates behind a verdict, not only the verdict", () => {
    // A delivery in March and a refusal last week are both facts; the verdict is just the more
    // recent one. Showing the dates lets an operator check it rather than trust it.
    render(<ReachabilityPanel />);

    const cells = within(screen.getByRole("table")).getAllByRole("cell");
    expect(cells[2]).toHaveTextContent("On WhatsApp");
    // Asserted by shape rather than by a formatted string, which varies with the test runner's
    // locale and would make this fail for a reason that has nothing to do with the panel.
    expect(cells[3]?.textContent).toMatch(/2026/);
    expect(cells[4]).toHaveTextContent("—"); // never refused
  });

  it("filters to one verdict when its tile is pressed, and clears on a second press", () => {
    render(<ReachabilityPanel />);
    const tile = screen.getByRole("button", { name: /Not on WhatsApp/ });

    fireEvent.click(tile);
    expect(state.asked.at(-1)?.verdict).toBe("unreachable");

    fireEvent.click(tile);
    expect(state.asked.at(-1)?.verdict).toBe("");
  });

  it("passes the search through to the query", () => {
    render(<ReachabilityPanel />);

    fireEvent.change(screen.getByLabelText("Search by name or number"), {
      target: { value: "99900" },
    });

    expect(state.asked.at(-1)?.q).toBe("99900");
  });

  it("tells an empty account what produces reachability", () => {
    state.result.data = page([]);
    state.counts.data = { reachable: 0, unreachable: 0, unknown: 0 };

    render(<ReachabilityPanel />);

    expect(screen.getByText(/send a campaign/i)).toBeInTheDocument();
  });

  it("says to narrow the filter when a filter is what emptied the list", () => {
    state.result.data = page([]);
    render(<ReachabilityPanel />);

    fireEvent.change(screen.getByLabelText("Search by name or number"), {
      target: { value: "nobody" },
    });

    expect(screen.getByText(/Clear the filter/i)).toBeInTheDocument();
  });

  it("does not present a failed query as an account with no contacts", () => {
    state.result = {
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("reachability is unavailable"),
      refetch: vi.fn(),
    };

    render(<ReachabilityPanel />);

    expect(screen.getByRole("alert")).toHaveTextContent(/unavailable/i);
  });

  it("admits when it is showing only the first page", () => {
    state.result.data = page([reached], true);

    render(<ReachabilityPanel />);

    expect(screen.getByText(/Showing the first/i)).toBeInTheDocument();
  });

  it("shows a dash for the tallies while they are still being counted", () => {
    // They are a separate, slower request on purpose -- 9ms for the page against 425ms for the
    // tallies at 200k recipients. A zero here would be read as "none", which is a different claim.
    state.counts = { data: undefined, isPending: true };

    render(<ReachabilityPanel />);

    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });

  it("counts the same population the list is showing", () => {
    render(<ReachabilityPanel />);

    fireEvent.change(screen.getByLabelText("Search by name or number"), {
      target: { value: "99900" },
    });

    expect(state.countsAsked.at(-1)).toBe("99900");
    expect(state.asked.at(-1)?.q).toBe("99900");
  });
});
