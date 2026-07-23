import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { cloneElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { toRangeQuery } from "@/features/analytics/api";
import { AnalyticsFilters } from "@/features/analytics/AnalyticsFilters";
import { BreakdownTable } from "@/features/analytics/BreakdownTable";
import { ExportActions } from "@/features/analytics/ExportActions";
import { delta, formatKpi, formatLag, formatMicros, formatRate, UNKNOWN } from "@/features/analytics/format";
import { KpiCards } from "@/features/analytics/KpiCards";
import { SeriesChart } from "@/features/analytics/SeriesChart";
import type { AnalyticsBreakdown, AnalyticsFilterState } from "@/features/analytics/types";

// Permission-gated surfaces read the session; the roster is swapped per test.
const permissions = { value: ["analytics:read", "analytics:export", "analytics:executive"] };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

// Recharts sizes its children from the container it measures, and jsdom reports 0x0. The mock
// supplies concrete dimensions so the SVG actually renders under test.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactElement }) => (
      <div data-testid="responsive-container">
        {cloneElement(children, { width: 800, height: 300 })}
      </div>
    ),
  };
});

const FILTERS: AnalyticsFilterState = {
  preset: "last_30d",
  from: "",
  to: "",
  granularity: "day",
  compare: "",
};

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  permissions.value = ["analytics:read", "analytics:export", "analytics:executive"];
});

// --- Query construction (Doc 15 §14.2) ----------------------------------------------------------
describe("toRangeQuery", () => {
  it("sends a preset without explicit bounds", () => {
    expect(toRangeQuery(FILTERS)).toEqual({ granularity: "day", preset: "last_30d" });
  });

  it("sends explicit bounds when no preset is set", () => {
    expect(
      toRangeQuery({ ...FILTERS, preset: "", from: "2026-07-01T00:00:00Z", to: "2026-07-08T00:00:00Z" }),
    ).toEqual({
      granularity: "day",
      from: "2026-07-01T00:00:00Z",
      to: "2026-07-08T00:00:00Z",
    });
  });

  it("never sends a preset and a range together — the API takes one or the other", () => {
    const query = toRangeQuery({ ...FILTERS, from: "2026-07-01T00:00:00Z" });
    expect(query).not.toHaveProperty("from");
    expect(query).toHaveProperty("preset");
  });
});

// --- Formatting: unknown is not zero (Doc 15 §11) -----------------------------------------------
describe("formatting", () => {
  it("renders a null rate as unknown rather than 0%", () => {
    expect(formatRate(null)).toBe(UNKNOWN);
    expect(formatRate(0)).toBe("0.0%");
    expect(formatRate(0.9903)).toBe("99.0%");
  });

  it("converts micro-units to currency amounts", () => {
    expect(formatMicros(1_250_000)).toBe("1.25");
    expect(formatMicros(null)).toBe(UNKNOWN);
  });

  it("formats each KPI kind", () => {
    expect(formatKpi(0.5, "rate")).toBe("50.0%");
    expect(formatKpi(90, "duration")).toBe("2m");
    expect(formatKpi(2_000_000, "micros")).toBe("2.00");
    expect(formatKpi(1234, "count")).toBe("1,234");
  });

  it("describes rollup lag in human terms", () => {
    expect(formatLag(30)).toBe("just now");
    expect(formatLag(1800)).toBe("30 min ago");
    expect(formatLag(null)).toBe("never run");
  });

  it("returns no delta when the previous value cannot support one", () => {
    expect(delta(10, 0)).toBeNull();
    expect(delta(10, null)).toBeNull();
    expect(delta(15, 10)).toBeCloseTo(0.5);
  });
});

// --- KPI cards ------------------------------------------------------------------------------------
describe("KpiCards", () => {
  const kpis = {
    delivery_rate: 0.99,
    read_rate: 0.5,
    failure_rate: 0.01,
    avg_delivery_latency_ms: null,
    resolution_rate: null,
    avg_first_response_seconds: null,
    avg_resolution_seconds: null,
    task_completion_rate: 0.75,
    task_on_time_rate: 0.8,
    avg_time_to_complete_seconds: null,
    net_opt_in_change: 30,
    opt_out_rate: 0.1,
    campaign_delivery_rate: null,
    campaign_click_through_rate: null,
    cost_per_delivered_micros: 2_500,
  };

  it("renders the headline indicators", () => {
    withProviders(<KpiCards kpis={kpis} />);
    expect(screen.getByText("Delivery rate")).toBeInTheDocument();
    expect(screen.getByText("99.0%")).toBeInTheDocument();
  });

  it("shows unknown for a KPI with no denominator", () => {
    withProviders(<KpiCards kpis={kpis} />);
    const card = screen.getByText("Avg first response").closest("div")!;
    expect(within(card).getByText(UNKNOWN)).toBeInTheDocument();
  });

  it("hides spend without analytics:executive", () => {
    const { unmount } = withProviders(<KpiCards kpis={kpis} />);
    expect(screen.getByText("Cost per delivered")).toBeInTheDocument();
    unmount();

    permissions.value = ["analytics:read"];
    withProviders(<KpiCards kpis={kpis} />);
    expect(screen.queryByText("Cost per delivered")).not.toBeInTheDocument();
  });

  it("renders a comparison delta when a previous window is supplied", () => {
    withProviders(<KpiCards kpis={kpis} previous={{ ...kpis, delivery_rate: 0.9 }} />);
    expect(screen.getAllByText(/vs previous/).length).toBeGreaterThan(0);
  });

  it("renders while data is still loading", () => {
    withProviders(<KpiCards kpis={undefined} />);
    expect(screen.getByText("Delivery rate")).toBeInTheDocument();
    expect(screen.getAllByText(UNKNOWN).length).toBeGreaterThan(0);
  });
});

// --- Filters --------------------------------------------------------------------------------------
describe("AnalyticsFilters", () => {
  it("emits a preset and clears any explicit range", () => {
    const onChange = vi.fn();
    render(<AnalyticsFilters filters={{ ...FILTERS, from: "2026-07-01T00:00:00Z" }} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Period"), { target: { value: "last_7d" } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ preset: "last_7d", from: "", to: "" }),
    );
  });

  it("emits an explicit range and clears the preset", () => {
    const onChange = vi.fn();
    render(<AnalyticsFilters filters={FILTERS} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-07-01" } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ preset: "", from: "2026-07-01T00:00:00Z" }),
    );
  });

  it("offers every documented granularity", () => {
    render(<AnalyticsFilters filters={FILTERS} onChange={vi.fn()} />);
    const select = screen.getByLabelText("Granularity") as HTMLSelectElement;
    expect([...select.options].map((option) => option.value)).toEqual([
      "hour", "day", "week", "month",
    ]);
  });

  it("offers both comparison windows plus none", () => {
    render(<AnalyticsFilters filters={FILTERS} onChange={vi.fn()} />);
    const select = screen.getByLabelText("Compare") as HTMLSelectElement;
    expect([...select.options].map((option) => option.value)).toEqual([
      "", "previous_period", "previous_year",
    ]);
  });
});

// --- Charts ---------------------------------------------------------------------------------------
describe("SeriesChart", () => {
  const series = [
    {
      key: "messages_sent",
      label: "Messages sent",
      points: [
        { t: "2026-07-01", v: 10 },
        { t: "2026-07-02", v: 20 },
      ],
    },
  ];

  it("renders an empty state rather than a blank chart", () => {
    const { container } = render(<SeriesChart series={[]} />);
    expect(screen.getByText("No data for this period")).toBeInTheDocument();
    expect(container.querySelector("svg")).toBeNull();
  });

  it("treats a series of empty points as no data", () => {
    render(<SeriesChart series={[{ key: "k", label: "K", points: [] }]} />);
    expect(screen.getByText("No data for this period")).toBeInTheDocument();
  });

  it("renders each supported chart kind", () => {
    for (const kind of ["line", "area", "bar"] as const) {
      const { container, unmount } = render(<SeriesChart series={series} kind={kind} />);
      expect(container.querySelector("svg")).not.toBeNull();
      unmount();
    }
  });

  it("renders stacked bars", () => {
    const { container } = render(<SeriesChart series={series} kind="bar" stacked />);
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("is responsive rather than fixed-width", () => {
    // The chart is wrapped in ResponsiveContainer, so its size comes from the layout, not a prop.
    render(<SeriesChart series={series} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("plots a point per period", () => {
    const { container } = render(<SeriesChart series={series} kind="bar" />);
    expect(container.querySelectorAll(".recharts-bar-rectangle").length).toBe(2);
  });
});

// --- Breakdown table ------------------------------------------------------------------------------
describe("BreakdownTable", () => {
  const data: AnalyticsBreakdown = {
    dimension: "error_code",
    grain: "hour",
    from: "2026-07-01T00:00:00Z",
    to: "2026-07-08T00:00:00Z",
    timezone: "UTC",
    data: [
      { key: "131047", label: "131047", totals: { failures: 8 }, kpis: {} as never },
      { key: "470", label: "470", totals: { failures: 4 }, kpis: {} as never },
    ],
    totals: { failures: 12 },
  };
  const query = { data, isLoading: false, isError: false, error: null, refetch: vi.fn() };

  it("renders ranked rows", () => {
    render(
      <BreakdownTable
        title="Error code"
        query={query}
        columns={[{ key: "failures", label: "Failures" }]}
      />,
    );
    expect(screen.getByText("131047")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
  });

  it("shows a spinner while loading", () => {
    render(
      <BreakdownTable
        title="Error code"
        query={{ ...query, data: undefined, isLoading: true }}
        columns={[{ key: "failures", label: "Failures" }]}
      />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows an error with a retry", () => {
    const refetch = vi.fn();
    render(
      <BreakdownTable
        title="Error code"
        query={{ ...query, data: undefined, isError: true, error: { detail: "boom" }, refetch }}
        columns={[{ key: "failures", label: "Failures" }]}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalled();
  });

  it("shows an empty state for a period with no rows", () => {
    render(
      <BreakdownTable
        title="Error code"
        query={{ ...query, data: { ...data, data: [] } }}
        columns={[{ key: "failures", label: "Failures" }]}
      />,
    );
    expect(screen.getByText("No data for this period")).toBeInTheDocument();
  });

  it("formats micro-unit columns as currency", () => {
    render(
      <BreakdownTable
        title="Type"
        query={{
          ...query,
          data: {
            ...data,
            data: [{ key: "text", label: "text", totals: { cost_micros: 2_500_000 }, kpis: {} as never }],
          },
        }}
        columns={[{ key: "cost_micros", label: "Spend" }]}
      />,
    );
    expect(screen.getByText("2.50")).toBeInTheDocument();
  });
});

// --- Export actions -------------------------------------------------------------------------------
describe("ExportActions", () => {
  it("is hidden without analytics:export", () => {
    permissions.value = ["analytics:read"];
    const { container } = withProviders(<ExportActions filters={FILTERS} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("offers every documented report and format", () => {
    withProviders(<ExportActions filters={FILTERS} />);

    const reports = screen.getByLabelText("Report") as HTMLSelectElement;
    const formats = screen.getByLabelText("Format") as HTMLSelectElement;
    expect([...reports.options].map((o) => o.value)).toEqual([
      "messages", "failures", "campaigns", "conversations", "tasks", "customers", "costs",
    ]);
    expect([...formats.options].map((o) => o.value)).toEqual(["csv", "xlsx", "json"]);
  });

  it("starts an export through the generated client", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      calls.push(url);
      return new Response(
        JSON.stringify({ job: { id: "exp-1", type: "export", status: "queued", poll_url: "/x" } }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      );
    });

    withProviders(<ExportActions filters={FILTERS} />);
    fireEvent.click(screen.getByRole("button", { name: "Export" }));

    await waitFor(() =>
      expect(calls.some((url) => url.includes("/api/v1/analytics/reports/export"))).toBe(true),
    );
    vi.unstubAllGlobals();
  });
});
