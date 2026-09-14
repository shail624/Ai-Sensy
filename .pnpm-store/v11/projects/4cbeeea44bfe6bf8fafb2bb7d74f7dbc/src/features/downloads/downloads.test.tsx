import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DownloadCenter } from "@/features/downloads/DownloadCenter";
import { useDownloads } from "@/features/downloads/api";
import type { DownloadItem, DownloadsPage } from "@/features/downloads/types";

vi.mock("@/features/downloads/api", () => ({
  apiErrorMessage: (error: unknown) => String(error),
  useDownloads: vi.fn(),
}));

const mockedUseDownloads = vi.mocked(useDownloads);

function item(overrides: Partial<DownloadItem> = {}): DownloadItem {
  return {
    id: "download-1",
    type: "download",
    category: "contacts",
    name: "Contacts export",
    format: "csv",
    status: "ready",
    row_count: 120,
    download_url: "/api/v1/artifacts/export-1?signature=valid",
    expires_at: "2026-08-25T12:00:00Z",
    created_at: "2026-08-24T12:00:00Z",
    completed_at: "2026-08-24T12:01:00Z",
    ...overrides,
  };
}

function page(rows: DownloadItem[], overrides: Partial<DownloadsPage["page"]> = {}): DownloadsPage {
  return {
    data: rows,
    page: {
      limit: 25,
      has_more: false,
      next_cursor: null,
      prev_cursor: null,
      total: rows.length,
      ...overrides,
    },
  };
}

function hook(data: DownloadsPage) {
  return {
    data,
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useDownloads>;
}

function renderCenter(path = "/downloads"): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <DownloadCenter />
    </MemoryRouter>,
  );
}

describe("DownloadCenter", () => {
  beforeEach(() => {
    mockedUseDownloads.mockReset();
  });

  it("renders ready, active, failed and expired jobs without exposing stale links", () => {
    mockedUseDownloads.mockReturnValue(
      hook(page([
        item(),
        item({ id: "download-chat", name: "Chat transcript", category: "chat_history", format: "pdf" }),
        item({ id: "download-campaign", name: "August recovery results", category: "campaigns", format: "xlsx" }),
        item({ id: "download-2", name: "Messages report", category: "analytics", status: "processing", download_url: null, row_count: null }),
        item({ id: "download-3", name: "Failures report", category: "analytics", status: "failed", download_url: null }),
        item({ id: "download-4", status: "expired", download_url: null }),
      ])),
    );

    renderCenter();

    expect(screen.getAllByRole("link", { name: "Download" })[0]).toHaveAttribute(
      "href",
      "/api/v1/artifacts/export-1?signature=valid",
    );
    const history = within(screen.getByRole("table"));
    expect(history.getByText("Preparing")).toBeInTheDocument();
    expect(history.getByText("Failed")).toBeInTheDocument();
    expect(history.getByText("Expired")).toBeInTheDocument();
    expect(screen.getByText("Link expired")).toBeInTheDocument();
    expect(screen.getByText("Chat transcript")).toBeInTheDocument();
    expect(screen.getByText("August recovery results")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Download" })).toHaveLength(3);
  });

  it("keeps filters in the URL-backed query and resets to the first page", () => {
    mockedUseDownloads.mockReturnValue(hook(page([item()])));
    renderCenter("/downloads?category=analytics&status=ready");

    expect(mockedUseDownloads).toHaveBeenLastCalledWith({
      category: "analytics",
      status: "ready",
      cursor: undefined,
    });
    fireEvent.change(screen.getByLabelText("Download status"), { target: { value: "failed" } });
    expect(mockedUseDownloads).toHaveBeenLastCalledWith({
      category: "analytics",
      status: "failed",
      cursor: undefined,
    });
  });

  it("offers campaign results as a first-class artifact family", () => {
    mockedUseDownloads.mockReturnValue(hook(page([])));
    renderCenter("/downloads?category=campaigns");

    expect(screen.getByRole("option", { name: "Campaign results" })).toBeInTheDocument();
    expect(mockedUseDownloads).toHaveBeenLastCalledWith({
      category: "campaigns",
      status: "all",
      cursor: undefined,
    });
  });

  it("uses the server cursor for next and previous history pages", () => {
    mockedUseDownloads.mockImplementation((query) =>
      hook(
        query.cursor
          ? page([item({ id: "older" })], { total: 2 })
          : page([item()], { has_more: true, next_cursor: "older-cursor", total: 2 }),
      ),
    );
    renderCenter();

    const pagination = screen.getByRole("navigation", { name: "Download history pagination" });
    fireEvent.click(within(pagination).getByRole("button", { name: "Next" }));
    expect(mockedUseDownloads).toHaveBeenLastCalledWith({
      category: "all",
      status: "all",
      cursor: "older-cursor",
    });
    fireEvent.click(within(pagination).getByRole("button", { name: "Previous" }));
    expect(mockedUseDownloads).toHaveBeenLastCalledWith({
      category: "all",
      status: "all",
      cursor: undefined,
    });
  });

  it("shows a useful first-run action when no export exists", () => {
    mockedUseDownloads.mockReturnValue(hook(page([])));
    renderCenter();

    expect(screen.getByText("No downloads yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create an analytics report" })).toHaveAttribute(
      "href",
      "/analytics",
    );
  });
});
