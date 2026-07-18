import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EmptyState, ErrorState, Section, TagChip } from "@/components/ui";

describe("ui primitives", () => {
  it("Section renders its title and children", () => {
    render(
      <Section title="Basic information">
        <p>hello</p>
      </Section>,
    );
    expect(screen.getByRole("heading", { name: /basic information/i })).toBeInTheDocument();
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("EmptyState renders title and description", () => {
    render(<EmptyState title="No tags yet" description="add one" />);
    expect(screen.getByText("No tags yet")).toBeInTheDocument();
    expect(screen.getByText("add one")).toBeInTheDocument();
  });

  it("ErrorState shows the message and calls onRetry", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Boom" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("TagChip renders and removes", () => {
    const onRemove = vi.fn();
    render(<TagChip name="vip" color="#22c55e" onRemove={onRemove} />);
    expect(screen.getByText("vip")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /remove tag vip/i }));
    expect(onRemove).toHaveBeenCalledOnce();
  });
});
