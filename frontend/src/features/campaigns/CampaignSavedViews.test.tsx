import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignSavedViews } from "@/features/campaigns/CampaignSavedViews";
import type { CampaignListQuery, CampaignView } from "@/features/campaigns/types";

const mocks = vi.hoisted(() => ({
  views: { value: [] as CampaignView[] },
  permissions: { value: [] as string[] },
  create: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/features/campaigns/api", () => ({
  useCampaignViews: () => ({
    data: mocks.views.value,
    isLoading: false,
    isError: false,
  }),
  useCreateCampaignView: () => ({
    mutate: mocks.create,
    isPending: false,
    error: null,
  }),
  useDeleteCampaignView: () => ({
    mutate: mocks.remove,
    isPending: false,
    error: null,
  }),
}));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (permission: string) => mocks.permissions.value.includes(permission),
}));

const QUERY: CampaignListQuery = {
  q: "  August  ",
  status: "running",
  sort: "-total_recipients",
  page: 7,
};

describe("CampaignSavedViews", () => {
  beforeEach(() => {
    mocks.views.value = [];
    mocks.permissions.value = [];
    mocks.create.mockReset();
    mocks.remove.mockReset();
  });

  it("applies a saved view and resets transient paging", () => {
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000301",
        name: "Scheduled broadcasts",
        visibility: "shared",
        display: "list",
        filters: { q: "Renewal", status: "scheduled", sort: "created_at" },
        is_owner: false,
        can_delete: false,
        created_at: "2026-08-25T10:00:00Z",
      },
    ];
    const onApply = vi.fn();
    render(<CampaignSavedViews query={QUERY} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "Scheduled broadcasts" }));

    expect(onApply).toHaveBeenCalledWith({
      q: "Renewal",
      status: "scheduled",
      sort: "created_at",
      page: 1,
    });
  });

  it("saves only portable list state and restricts team publishing", () => {
    render(<CampaignSavedViews query={QUERY} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    expect(screen.getByRole("option", { name: "Whole team" })).toBeDisabled();
    expect(screen.getByText(/Your role can save personal views/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "My active campaigns" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));

    expect(mocks.create).toHaveBeenCalledWith(
      {
        name: "My active campaigns",
        visibility: "private",
        display: "list",
        filters: {
          q: "August",
          status: "running",
          sort: "-total_recipients",
        },
      },
      expect.any(Object),
    );
  });

  it("lets a Campaign manager publish and confirm deletion of a team view", () => {
    mocks.permissions.value = ["campaigns:views_manage"];
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000302",
        name: "Team campaigns",
        visibility: "shared",
        display: "list",
        filters: { sort: "-created_at" },
        is_owner: true,
        can_delete: true,
        created_at: "2026-08-25T10:00:00Z",
      },
    ];
    render(<CampaignSavedViews query={QUERY} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    fireEvent.change(screen.getByLabelText("Visible to"), { target: { value: "shared" } });
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "Managers broadcasts" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Managers broadcasts", visibility: "shared" }),
      expect.any(Object),
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete Team campaigns" }));
    expect(screen.getByText("Delete “Team campaigns”?" )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete view" }));
    expect(mocks.remove).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000302",
      expect.any(Object),
    );
  });
});
