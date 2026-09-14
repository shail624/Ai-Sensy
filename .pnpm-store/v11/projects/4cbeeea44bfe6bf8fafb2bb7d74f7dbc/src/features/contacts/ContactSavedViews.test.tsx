import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ContactSavedViews } from "@/features/contacts/ContactSavedViews";
import type { ContactFilters } from "@/features/contacts/buildRules";
import type { ContactView } from "@/features/contacts/types";

const mocks = vi.hoisted(() => ({
  views: { value: [] as ContactView[] },
  permissions: { value: [] as string[] },
  create: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/features/contacts/api", () => ({
  useContactViews: () => ({
    data: mocks.views.value,
    isLoading: false,
    isError: false,
  }),
  useCreateContactView: () => ({
    mutate: mocks.create,
    isPending: false,
    error: null,
  }),
  useDeleteContactView: () => ({
    mutate: mocks.remove,
    isPending: false,
    error: null,
  }),
}));

vi.mock("@/lib/auth", () => ({
  useHasPermission: (permission: string) => mocks.permissions.value.includes(permission),
}));

const FILTERS: ContactFilters = {
  search: "Asha",
  tagId: "11111111-1111-4111-8111-111111111111",
  attributes: { reactivation_status: "pending", empty_filter: "" },
};

describe("ContactSavedViews", () => {
  beforeEach(() => {
    mocks.views.value = [];
    mocks.permissions.value = [];
    mocks.create.mockReset();
    mocks.remove.mockReset();
  });

  it("applies a saved view and drops the current cursor through the parent filter contract", () => {
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000201",
        name: "VIP contacts",
        visibility: "shared",
        display: "list",
        filters: {
          q: "Priya",
          tag_id: "22222222-2222-4222-8222-222222222222",
          attributes: { customer_type: "VIP" },
        },
        is_owner: false,
        can_delete: false,
        created_at: "2026-08-24T10:00:00Z",
      },
    ];
    const onApply = vi.fn();
    render(<ContactSavedViews filters={FILTERS} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "VIP contacts" }));

    expect(onApply).toHaveBeenCalledWith({
      search: "Priya",
      tagId: "22222222-2222-4222-8222-222222222222",
      attributes: { customer_type: "VIP" },
    });
  });

  it("saves only portable active filters and restricts team publishing", () => {
    render(<ContactSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    expect(screen.getByRole("option", { name: "Whole team" })).toBeDisabled();
    expect(screen.getByText(/Your role can save personal views/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "My follow-ups" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));

    expect(mocks.create).toHaveBeenCalledWith(
      {
        name: "My follow-ups",
        visibility: "private",
        display: "list",
        filters: {
          q: "Asha",
          tag_id: "11111111-1111-4111-8111-111111111111",
          attributes: { reactivation_status: "pending" },
        },
      },
      expect.any(Object),
    );
  });

  it("lets a Contacts manager publish and confirm deletion of a team view", () => {
    mocks.permissions.value = ["contacts:views_manage"];
    mocks.views.value = [
      {
        id: "00000000-0000-4000-8000-000000000202",
        name: "Team pending",
        visibility: "shared",
        display: "list",
        filters: { attributes: { reactivation_status: "pending" } },
        is_owner: true,
        can_delete: true,
        created_at: "2026-08-24T10:00:00Z",
      },
    ];
    render(<ContactSavedViews filters={FILTERS} onApply={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save / manage" }));

    fireEvent.change(screen.getByLabelText("Visible to"), { target: { value: "shared" } });
    fireEvent.change(screen.getByLabelText("View name"), {
      target: { value: "Managers queue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save current view" }));
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Managers queue", visibility: "shared" }),
      expect.any(Object),
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete Team pending" }));
    expect(screen.getByText("Delete “Team pending”?" )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete view" }));
    expect(mocks.remove).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000202",
      expect.any(Object),
    );
  });
});
