import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WebhooksPanel } from "@/features/operations/OperationsPanels";

const state = vi.hoisted(() => ({
  canOperate: true,
  events: {
    data: undefined as unknown,
    isPending: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
  deadLetters: {
    data: undefined as unknown,
    isPending: false,
    isError: false,
    error: null as unknown,
    refetch: vi.fn(),
  },
}));

vi.mock("@/features/operations/api", () => ({
  useHasPermission: () => state.canOperate,
  useWebhookEvents: () => state.events,
  useWebhookDeadLetters: () => state.deadLetters,
}));

vi.mock("@/features/channels/api", () => ({
  useWabas: () => ({ data: [{ id: "w1" }], isLoading: false, isError: false, error: null }),
  useNumbers: () => ({ data: [{ id: "n1" }], isLoading: false, isError: false, error: null }),
}));

function page<T>(rows: T[], total: number) {
  return { data: rows, page: { limit: 50, has_more: false, next_cursor: null, total } };
}

const delivery = {
  event_id: "wamid.ABC",
  object_type: "message",
  status: "processed",
  attempts: 1,
  signature_ok: true,
  created_at: "2026-09-16T09:00:00Z",
  processed_at: "2026-09-16T09:00:01Z",
};

function renderPanel() {
  return render(
    <MemoryRouter>
      <WebhooksPanel />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  state.canOperate = true;
  state.events = { data: page([delivery], 1), isPending: false, isError: false, error: null, refetch: vi.fn() };
  state.deadLetters = { data: page([], 0), isPending: false, isError: false, error: null, refetch: vi.fn() };
});

describe("WebhooksPanel", () => {
  it("reports a delivery with the state an operator needs", () => {
    renderPanel();

    expect(screen.getByText("message")).toBeInTheDocument();
    expect(screen.getByText("processed")).toBeInTheDocument();
    expect(screen.getByText("verified")).toBeInTheDocument();
  });

  it("flags a delivery whose signature did not verify", () => {
    state.events.data = page([{ ...delivery, signature_ok: false, status: "failed" }], 1);

    renderPanel();

    expect(screen.getByText("unverified")).toBeInTheDocument();
  });

  it("shows the error that stopped a parked event", () => {
    // Without the error an operator sees that something failed but not what to do about it.
    state.deadLetters.data = page(
      [
        {
          id: "11111111-1111-4111-8111-111111111111",
          error_detail: "contact lookup timed out",
          attempts: 5,
          status: "pending",
          created_at: "2026-09-16T08:00:00Z",
          replayed_at: null,
        },
      ],
      1,
    );

    renderPanel();

    expect(screen.getByText("contact lookup timed out")).toBeInTheDocument();
    expect(screen.getByText("5 attempts")).toBeInTheDocument();
  });

  it("says plainly when nothing is parked rather than leaving a blank card", () => {
    renderPanel();

    expect(screen.getByText(/Nothing is parked/i)).toBeInTheDocument();
  });

  it("distinguishes an empty delivery log from a broken one", () => {
    // "No traffic" and "the query failed" look identical if both render as nothing, and they call
    // for opposite actions: check the channel, or check the platform.
    state.events.data = page([], 0);

    renderPanel();

    expect(screen.getByText(/No deliveries recorded/i)).toBeInTheDocument();
  });

  it("surfaces a failed delivery query with a retry", () => {
    state.events = {
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("upstream said no"),
      refetch: vi.fn(),
    };

    renderPanel();

    expect(screen.getByRole("alert")).toHaveTextContent(/upstream said no/i);
  });

  it("gates the tables, not the whole panel, when the viewer lacks webhooks:manage", () => {
    // `/operations/webhooks` is reachable with `waba:read`; the delivery log needs more. Hiding
    // everything would tell a legitimate reader the page was broken.
    state.canOperate = false;

    renderPanel();

    expect(screen.getByText(/Connected numbers/i)).toBeInTheDocument();
    expect(screen.getByText(/requires webhook permissions/i)).toBeInTheDocument();
    expect(screen.queryByText("wamid.ABC")).not.toBeInTheDocument();
  });

  it("counts parked events where someone scanning the page will see it", () => {
    state.deadLetters.data = page([], 3);

    renderPanel();

    expect(screen.getByText("Parked for a human")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
