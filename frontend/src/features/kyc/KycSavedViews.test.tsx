import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  KycSavedViews,
  type KycPortableFilters,
} from "@/features/kyc/KycSavedViews";
import type { KycView } from "@/features/kyc/types";

const mocks = vi.hoisted(() => ({
  views: { value: [] as KycView[] },
  permissions: { value: [] as string[] },
  create: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/features/kyc/api", () => ({
  useKycViews: () => ({
    data: mocks.views.value,
    isLoading: false,
    isError: false,
  }),
  useCreateKycView: () => ({
    mutate: mocks.create,
    isPending: false,
    error: null,
  }),
  useDeleteKycView: () => ({
    mutate: mocks.remove,
    isPending: false,
    error: null,
  }),
}));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (permission: string) => mocks.permissions.value.includes(permission),
}));

const FILTERS: KycPortableFilters = {
  q: "  Asha  ",
  status: "documents_pending",
};

describe("KycSavedViews", () => {
  beforeEach(() => {
    mocks.views.value = [];
    mocks.permissions.value = [];
    mocks.create.mockReset();
    mocks.remove.mockReset();
  });

  it("applies only the saved portable KYC queue filters", () => {
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000401",
        name: "Team reviews",
        visibility: "shared",
        display: "list",
        filters: { q: "Renewal", status: "under_review" },
        is_owner: false,
        can_delete: false,
        created_at: "2026-08-26T10:00:00Z",
      },
    ];
    const onApply = vi.fn();
    render(<KycSavedViews filters={FILTERS} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "Team reviews" }));

    expect(onApply).toHaveBeenCalledWith({ q: "Renewal", status: "under_review" });
  });

  it("saves trimmed portable state and restricts team publishing", () => {
    render(<KycSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    expect(screen.getByRole("option", { name: "Whole team" })).toBeDisabled();
    expect(screen.getByText(/Your role can save personal views/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "My document queue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));

    expect(mocks.create).toHaveBeenCalledWith(
      {
        name: "My document queue",
        visibility: "private",
        display: "list",
        filters: { q: "Asha", status: "documents_pending" },
      },
      expect.any(Object),
    );
  });

  it("lets a KYC manager publish and confirm deletion of a team view", () => {
    mocks.permissions.value = ["kyc:views_manage"];
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000402",
        name: "Manager queue",
        visibility: "shared",
        display: "list",
        filters: { status: "under_review" },
        is_owner: true,
        can_delete: true,
        created_at: "2026-08-26T10:00:00Z",
      },
    ];
    render(<KycSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    fireEvent.change(screen.getByLabelText("Visible to"), { target: { value: "shared" } });
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "KYC team reviews" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "KYC team reviews", visibility: "shared" }),
      expect.any(Object),
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete Manager queue" }));
    expect(screen.getByText("Delete “Manager queue”?" )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete view" }));
    expect(mocks.remove).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000402",
      expect.any(Object),
    );
  });
});
