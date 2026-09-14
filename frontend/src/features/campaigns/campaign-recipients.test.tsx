import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignRecipients } from "@/features/campaigns/CampaignRecipients";

const state = vi.hoisted(() => ({
  calls: [] as Array<{ campaignId: string; status: string; cursor?: string }>,
}));

function recipient(overrides: Record<string, unknown> = {}) {
  return {
    contact_id: "contact-1",
    contact_name: "Aarav Mehta",
    wa_id: "919990000001",
    status: "sent",
    variables: null,
    error_code: null,
    retry_count: 0,
    queued_at: "2026-08-24T10:00:00Z",
    sent_at: "2026-08-24T10:01:00Z",
    delivered_at: null,
    read_at: null,
    failed_at: null,
    created_at: "2026-08-24T09:59:00Z",
    ...overrides,
  };
}

vi.mock("@/features/campaigns/api", () => ({
  apiErrorMessage: (error: unknown) => String(error),
  useCampaignRecipients: (
    campaignId: string,
    query: { status: string; cursor?: string },
  ) => {
    state.calls.push({ campaignId, ...query });
    const filtered = query.status === "failed";
    const second = query.cursor === "recipient-cursor-2";
    return {
      data: filtered
        ? {
            data: [
              recipient({
                contact_id: "contact-failed",
                contact_name: "Failed Customer",
                wa_id: "919990000099",
                status: "failed",
                error_code: "131026",
                retry_count: 2,
                sent_at: null,
                failed_at: "2026-08-24T10:02:00Z",
              }),
            ],
            page: { limit: 50, has_more: false, next_cursor: null, total: 1 },
            has_more: false,
          }
        : second
          ? {
              data: [recipient({ contact_id: "contact-2", contact_name: "Second Page" })],
              page: { limit: 50, has_more: false, next_cursor: null, total: 51 },
              has_more: false,
            }
          : {
              data: [recipient()],
              page: {
                limit: 50,
                has_more: true,
                next_cursor: "recipient-cursor-2",
                total: 51,
              },
              has_more: true,
            },
      isLoading: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    };
  },
}));

function renderLedger(): void {
  render(
    <MemoryRouter>
      <CampaignRecipients campaignId="campaign-1" />
    </MemoryRouter>,
  );
}

describe("CampaignRecipients", () => {
  beforeEach(() => {
    state.calls = [];
  });

  it("pages the complete server ledger and shows current contact identity", () => {
    renderLedger();

    expect(screen.getByText("Aarav Mehta")).toBeInTheDocument();
    expect(screen.getByText("51 total recipients")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Second Page")).toBeInTheDocument();
    expect(state.calls.at(-1)).toEqual({
      campaignId: "campaign-1",
      status: "",
      cursor: "recipient-cursor-2",
    });

    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getByText("Aarav Mehta")).toBeInTheDocument();
  });

  it("filters on the server and exposes the safe failure code and retry count", () => {
    renderLedger();
    fireEvent.change(screen.getByLabelText("Filter recipients by status"), {
      target: { value: "failed" },
    });

    expect(screen.getByText("Failed Customer")).toBeInTheDocument();
    expect(screen.getByText("131026")).toBeInTheDocument();
    expect(screen.getByText("1 failed recipient")).toBeInTheDocument();
    expect(state.calls.at(-1)).toEqual({
      campaignId: "campaign-1",
      status: "failed",
      cursor: undefined,
    });
  });
});
