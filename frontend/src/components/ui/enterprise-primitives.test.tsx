import { fireEvent, render, screen } from "@testing-library/react";
import { Search, X } from "lucide-react";
import { describe, expect, it, vi } from "vitest";

import {
  Button,
  Field,
  FilterBar,
  Input,
  Pagination,
  Select,
  Textarea,
  Toolbar,
  ToolbarDivider,
  ToolbarGroup,
} from "@/components/ui";

function PrimitiveHarness(): JSX.Element {
  return (
    <div>
      <Toolbar label="Customer actions" surface>
        <ToolbarGroup grow>
          <Button variant="secondary">Import</Button>
          <ToolbarDivider />
          <Button>New contact</Button>
        </ToolbarGroup>
      </Toolbar>

      <FilterBar label="Customer filters">
        <Field htmlFor="customer-search" label="Search" description="Search by name or number">
          <Input
            id="customer-search"
            type="search"
            leadingIcon={<Search aria-hidden className="h-4 w-4" />}
            trailingAction={
              <button type="button" aria-label="Clear search">
                <X aria-hidden className="h-4 w-4" />
              </button>
            }
          />
        </Field>
        <Field htmlFor="customer-status" label="Status">
          <Select id="customer-status" defaultValue="active">
            <option value="active">Active</option>
            <option value="closed">Closed</option>
          </Select>
        </Field>
        <Field htmlFor="customer-note" label="Note" error="A note is required">
          <Textarea id="customer-note" invalid />
        </Field>
      </FilterBar>
    </div>
  );
}

describe("enterprise UI primitives", () => {
  it("preserves semantic labels, descriptions, actions and invalid states", () => {
    render(<PrimitiveHarness />);

    expect(screen.getByLabelText("Customer actions")).toBeInTheDocument();
    expect(screen.getByLabelText("Customer filters")).toBeInTheDocument();
    expect(screen.getByLabelText("Search")).toHaveAttribute("type", "search");
    expect(screen.getByText("Search by name or number")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toHaveValue("active");
    expect(screen.getByLabelText("Note")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("A note is required");
    expect(screen.getByRole("button", { name: "Clear search" })).toBeEnabled();
  });

  it("keeps cursor pagination disabled states and callbacks truthful", () => {
    const previous = vi.fn();
    const next = vi.fn();
    render(
      <Pagination
        hasPrevious={false}
        hasNext
        onPrevious={previous}
        onNext={next}
        summary="25 of 100 contacts"
      />,
    );

    const pagination = screen.getByRole("navigation", { name: "Pagination" });
    expect(pagination).toHaveClass("flex-wrap");
    expect(screen.getByText("25 of 100 contacts")).toHaveClass("basis-full");
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(previous).not.toHaveBeenCalled();
    expect(next).toHaveBeenCalledOnce();
  });

  it("announces loading buttons without changing their accessible name", () => {
    render(<Button loading>Save changes</Button>);
    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});
