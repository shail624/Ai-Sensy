import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReportSavedViews } from "@/features/analytics/ReportSavedViews";
import type {
  AnalyticsFilterState,
  ReportView,
} from "@/features/analytics/types";

const mocks = vi.hoisted(() => ({
  views: { value: [] as ReportView[] },
  permissions: { value: [] as string[] },
  create: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/features/analytics/api", () => ({
  useReportViews: () => ({
    data: mocks.views.value,
    isLoading: false,
    isError: false,
  }),
  useCreateReportView: () => ({
    mutate: mocks.create,
    isPending: false,
    error: null,
  }),
  useDeleteReportView: () => ({
    mutate: mocks.remove,
    isPending: false,
    error: null,
  }),
}));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (permission: string) => mocks.permissions.value.includes(permission),
}));

const FILTERS: AnalyticsFilterState = {
  preset: "this_month",
  from: "",
  to: "",
  granularity: "day",
  compare: "previous_period",
};

describe("ReportSavedViews", () => {
  beforeEach(() => {
    mocks.views.value = [];
    mocks.permissions.value = [];
    mocks.create.mockReset();
    mocks.remove.mockReset();
  });

  it("applies only the saved portable report analysis filters", () => {
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000501",
        name: "Monthly leadership",
        visibility: "shared",
        display: "list",
        filters: {
          preset: "this_month",
          granularity: "week",
          compare: "previous_year",
        },
        is_owner: false,
        can_delete: false,
        created_at: "2026-08-26T10:00:00Z",
      },
    ];
    const onApply = vi.fn();
    render(<ReportSavedViews filters={FILTERS} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "Monthly leadership" }));

    expect(onApply).toHaveBeenCalledWith({
      preset: "this_month",
      from: "",
      to: "",
      granularity: "week",
      compare: "previous_year",
    });
  });

  it("saves portable state and restricts team publishing", () => {
    render(<ReportSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    expect(screen.getByRole("option", { name: "Whole team" })).toBeDisabled();
    expect(screen.getByText(/Your role can save personal views/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "My monthly report" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));

    expect(mocks.create).toHaveBeenCalledWith(
      {
        name: "My monthly report",
        visibility: "private",
        display: "list",
        filters: {
          preset: "this_month",
          granularity: "day",
          compare: "previous_period",
        },
      },
      expect.any(Object),
    );
  });

  it("lets a Reports manager publish and confirm deletion of a team view", () => {
    mocks.permissions.value = ["analytics:views_manage"];
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000502",
        name: "Executive comparison",
        visibility: "shared",
        display: "list",
        filters: { preset: "last_30d", granularity: "day" },
        is_owner: true,
        can_delete: true,
        created_at: "2026-08-26T10:00:00Z",
      },
    ];
    render(<ReportSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    fireEvent.change(screen.getByLabelText("Visible to"), { target: { value: "shared" } });
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "Leadership view" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Leadership view", visibility: "shared" }),
      expect.any(Object),
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete Executive comparison" }));
    expect(screen.getByText("Delete “Executive comparison”?" )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete view" }));
    expect(mocks.remove).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000502",
      expect.any(Object),
    );
  });
});
