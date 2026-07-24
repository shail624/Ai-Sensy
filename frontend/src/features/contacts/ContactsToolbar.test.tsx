import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContactsToolbar } from "@/features/contacts/ContactsToolbar";
import type { ContactFilters } from "@/features/contacts/buildRules";
import type { AttributeDefinition, Tag } from "@/features/contacts/types";

const TAGS: Tag[] = [
  {
    id: "t1",
    type: "tag",
    name: "VIP",
    color: "#ff0000",
    description: null,
    usage_count: 3,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  },
];

const ATTRIBUTES: AttributeDefinition[] = [
  {
    id: "a1",
    type: "custom_attribute",
    key_name: "reactivation_status",
    label: "Reactivation status",
    data_type: "enum",
    enum_values: ["pending", "won"],
    is_indexed: true,
    is_pii: false,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  },
];

const EMPTY: ContactFilters = { search: "", tagId: "", attributes: {} };

/** Force the compact (phone) branch: only `max-width` queries match. */
function useCompactViewport(): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("max-width"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

function renderToolbar(filters: Partial<ContactFilters> = {}, onChange = vi.fn()) {
  render(
    <ContactsToolbar
      filters={{ ...EMPTY, ...filters }}
      onChange={onChange}
      tags={TAGS}
      enumAttributes={ATTRIBUTES}
    />,
  );
  return onChange;
}

describe("ContactsToolbar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the filter dropdowns inline on desktop", () => {
    renderToolbar();
    expect(screen.getByLabelText("Filter by tag")).toBeInTheDocument();
    expect(screen.getByLabelText("Filter by Reactivation status")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /filters/i })).not.toBeInTheDocument();
  });

  it("moves the dropdowns into a bottom sheet on phones", () => {
    useCompactViewport();
    renderToolbar();

    expect(screen.queryByLabelText("Filter by tag")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Search contacts")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /filters/i }));

    const sheet = screen.getByRole("dialog");
    expect(sheet).toHaveAttribute("aria-label", "Filters");
    expect(screen.getByLabelText("Tag")).toBeInTheDocument();
    expect(screen.getByLabelText("Reactivation status")).toBeInTheDocument();
  });

  it("keeps the onChange contract from inside the sheet", () => {
    useCompactViewport();
    const onChange = renderToolbar();

    fireEvent.click(screen.getByRole("button", { name: /filters/i }));
    fireEvent.change(screen.getByLabelText("Tag"), { target: { value: "t1" } });

    expect(onChange).toHaveBeenCalledWith({ search: "", tagId: "t1", attributes: {} });
  });

  it("counts the active filters on the trigger and clears them from the sheet", () => {
    useCompactViewport();
    const onChange = renderToolbar({ tagId: "t1", attributes: { reactivation_status: "pending" } });

    const trigger = screen.getByRole("button", { name: /filters/i });
    expect(trigger).toHaveTextContent("2");

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));

    expect(onChange).toHaveBeenCalledWith({ search: "", tagId: "", attributes: {} });
  });
});
