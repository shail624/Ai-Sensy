import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignResultsExportDialog } from "@/features/campaigns/CampaignResultsExportDialog";
import type { Campaign } from "@/features/campaigns/types";

const state = vi.hoisted(() => ({
  mutate: vi.fn(),
  progress: null as null | {
    id: string;
    type: string;
    status: string;
    format: string;
    row_count: number | null;
    download_url: string | null;
    expires_at: string | null;
    created_at: string;
    completed_at: string | null;
  },
}));

vi.mock("@/features/campaigns/api", () => ({
  apiErrorMessage: (error: unknown) => String(error),
  useStartCampaignResultsExport: () => ({
    mutate: state.mutate,
    isPending: false,
    error: null,
  }),
  useCampaignResultsExport: () => ({
    data: state.progress,
    isError: false,
    error: null,
  }),
}));

const campaign = {
  id: "campaign-1",
  type: "campaign",
  name: "August recovery",
  phone_number_id: "phone-1",
  template_id: "template-1",
  status: "completed",
  audience_type: "segment",
  audience_ref: { segment_id: "segment-1" },
  variable_map: { header: [], body: [] },
  total_recipients: 120,
  queued_count: 120,
  sent_count: 118,
  delivered_count: 110,
  read_count: 75,
  failed_count: 2,
  replied_count: 10,
  row_version: 4,
  created_at: "2026-08-24T10:00:00Z",
  updated_at: "2026-08-24T10:30:00Z",
} as Campaign;

function renderDialog(): void {
  render(
    <MemoryRouter>
      <CampaignResultsExportDialog campaign={campaign} onClose={vi.fn()} />
    </MemoryRouter>,
  );
}

describe("CampaignResultsExportDialog", () => {
  beforeEach(() => {
    state.progress = null;
    state.mutate.mockReset();
    state.mutate.mockImplementation((_variables, options) => {
      options?.onSuccess?.({
        job: {
          id: "export-1",
          type: "export",
          status: "queued",
          poll_url: "/api/v1/campaigns/campaign-1/exports/export-1",
        },
      });
    });
  });

  it("submits a full-ledger status-filtered export and explains the privacy boundary", () => {
    renderDialog();

    expect(screen.getByText(/complete persisted recipient ledger/)).toBeInTheDocument();
    expect(screen.getByText(/Provider IDs, message IDs/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("File format"), { target: { value: "csv" } });
    fireEvent.change(screen.getByLabelText("Recipient status"), { target: { value: "failed" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate results" }));

    expect(state.mutate).toHaveBeenCalledWith(
      {
        campaignId: "campaign-1",
        body: { format: "csv", status: "failed" },
      },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(screen.getByText("Preparing results…")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Download Center/ })).toHaveAttribute(
      "href",
      "/downloads?category=campaigns",
    );
  });

  it("offers the ready signed artifact and factual row count", () => {
    state.progress = {
      id: "export-1",
      type: "export",
      status: "ready",
      format: "xlsx",
      row_count: 120,
      download_url: "/api/v1/artifacts/campaign-results?signature=valid",
      expires_at: "2026-08-25T10:00:00Z",
      created_at: "2026-08-24T10:00:00Z",
      completed_at: "2026-08-24T10:01:00Z",
    };
    renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "Generate results" }));

    expect(screen.getByText("120 recipients included.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download file" })).toHaveAttribute(
      "href",
      "/api/v1/artifacts/campaign-results?signature=valid",
    );
  });
});
