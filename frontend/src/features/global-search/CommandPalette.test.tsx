import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { moveActiveIndex, useDebouncedValue } from "./CommandPalette";

function DebounceHarness(): JSX.Element {
  const [value, setValue] = useState("");
  const debounced = useDebouncedValue(value, 250);
  return (
    <div>
      <button type="button" onClick={() => setValue("reactivation")}>Search</button>
      <output>{debounced}</output>
    </div>
  );
}

describe("CommandPalette quality controls", () => {
  afterEach(() => vi.useRealTimers());

  it("keeps keyboard selection valid for empty and bounded result collections", () => {
    expect(moveActiveIndex(0, 1, 0)).toBe(0);
    expect(moveActiveIndex(-1, 1, 3)).toBe(1);
    expect(moveActiveIndex(2, 1, 3)).toBe(2);
    expect(moveActiveIndex(0, -1, 3)).toBe(0);
  });

  it("debounces workspace search input before record queries may run", async () => {
    vi.useFakeTimers();
    const { container } = render(<DebounceHarness />);
    const output = container.querySelector("output");

    expect(output).not.toBeNull();
    expect(output).toHaveTextContent("");
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(output).toHaveTextContent("");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(249);
    });
    expect(output).toHaveTextContent("");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(output).toHaveTextContent("reactivation");
  });
});
