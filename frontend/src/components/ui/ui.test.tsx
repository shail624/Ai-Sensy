import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Badge, EmptyState, ErrorState, Modal, Section, TagChip } from "@/components/ui";

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

describe("Modal focus management (DS-10)", () => {
  function open(onClose = vi.fn()) {
    const invoker = document.createElement("button");
    document.body.appendChild(invoker);
    invoker.focus();
    const view = render(
      <Modal title="Filters" onClose={onClose}>
        <button type="button">First</button>
        <button type="button">Last</button>
      </Modal>,
    );
    return { invoker, onClose, view };
  }

  it("moves focus into the dialog on open", () => {
    open();
    expect(document.activeElement).toBe(screen.getByRole("dialog"));
  });

  it("wraps Tab from the last control back to the first, which is the close control", () => {
    open();
    screen.getByRole("button", { name: "Last" }).focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Close dialog" }));
  });

  it("wraps Shift+Tab from the dialog to the last control", () => {
    open();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Last" }));
  });

  it("closes on Escape and returns focus to whatever opened it", () => {
    const { invoker, onClose, view } = open();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
    view.unmount();
    expect(document.activeElement).toBe(invoker);
    invoker.remove();
  });

  it("Badge carries its hover explanation", () => {
    render(<Badge title="Rules changed since the last evaluation">Not evaluated</Badge>);
    expect(screen.getByText("Not evaluated")).toHaveAttribute(
      "title",
      "Rules changed since the last evaluation",
    );
  });
});
