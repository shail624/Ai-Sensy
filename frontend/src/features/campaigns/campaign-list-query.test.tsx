import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCampaigns } from "./api";
import { CampaignList } from "./CampaignList";

const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({ api: { GET: get } }));
vi.mock("@/lib/auth", () => ({ useHasPermission: () => true }));

function wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
let client: QueryClient;
beforeEach(() => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  get.mockReset().mockResolvedValue({ data: { data: [] } });
});

describe("campaign server filters", () => {
  it("offers truthful campaign shortcuts, refresh and report-download discovery", async () => {
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/campaigns?q=Alpha"]}><CampaignList /></MemoryRouter></QueryClientProvider>);
    await screen.findByText("No campaigns match these filters");

    expect(screen.getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("link", { name: "Report downloads" })).toHaveAttribute(
      "href",
      "/downloads?category=campaigns",
    );
    // Launch now asks for the campaign type first, as the reference does.
    fireEvent.click(screen.getByRole("button", { name: "Launch campaign" }));
    expect(screen.getByRole("heading", { name: "Select Campaign Type" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Meta Ads: next" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }));

    fireEvent.click(screen.getByRole("tab", { name: "Scheduled" }));
    await waitFor(() =>
      expect(get).toHaveBeenCalledWith("/api/v1/campaigns", {
        params: { query: { q: "Alpha", status: "scheduled" } },
      }),
    );
    expect(screen.getByRole("tab", { name: "Scheduled" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const refreshButton = await screen.findByRole("button", { name: "Refresh" });
    const callsBeforeRefresh = get.mock.calls.length;
    fireEvent.click(refreshButton);
    await waitFor(() => expect(get.mock.calls.length).toBeGreaterThan(callsBeforeRefresh));

    fireEvent.click(screen.getByRole("tab", { name: "All" }));
    await waitFor(() =>
      expect(get).toHaveBeenCalledWith("/api/v1/campaigns", {
        params: { query: { q: "Alpha" } },
      }),
    );
  });

  it("wires URL filters to the server and distinguishes no matches from an empty registry", async () => {
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/campaigns?q=Alpha&status=draft"]}><CampaignList /></MemoryRouter></QueryClientProvider>);
    await screen.findByText("No campaigns match these filters");
    expect(screen.queryByText("No campaigns yet")).not.toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/api/v1/campaigns", { params: { query: { q: "Alpha", status: "draft" } } });
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Beta" } });
    expect(screen.getByLabelText("Search")).toHaveValue("Beta");
    await waitFor(() => expect(get).toHaveBeenCalledWith("/api/v1/campaigns", { params: { query: { q: "Beta", status: "draft" } } }));
  });
  it("passes q and status through the client and refetches for each filter key", async () => {
    const { result, rerender } = renderHook(({ q, status }) => useCampaigns(true, { q, status }), {
      initialProps: { q: "Alpha", status: "draft" }, wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/api/v1/campaigns", { params: { query: { q: "Alpha", status: "draft" } } });
    rerender({ q: "Beta", status: "running" });
    await waitFor(() => expect(get).toHaveBeenCalledWith("/api/v1/campaigns", { params: { query: { q: "Beta", status: "running" } } }));
  });
  it("preserves unfiltered picker calls and disabled access", async () => {
    const { result, rerender } = renderHook(({ enabled }) => useCampaigns(enabled), { initialProps: { enabled: false }, wrapper });
    expect(get).not.toHaveBeenCalled();
    rerender({ enabled: true });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/api/v1/campaigns", { params: { query: {} } });
  });
});
