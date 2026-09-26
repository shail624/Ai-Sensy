import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { TemplateCreatePage } from "@/pages/TemplateCreatePage";

vi.mock("@/features/ai", () => ({
  AiFoundationPanel: () => <div>Assistant controls</div>,
}));

vi.mock("@/features/templates", () => ({
  cloneDraft: vi.fn(),
  TemplateEditor: () => <div>Template editor</div>,
}));

describe("TemplateCreatePage", () => {
  it("keeps the primary editor visible and the optional assistant collapsed by default", () => {
    render(
      <MemoryRouter>
        <TemplateCreatePage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Template editor")).toBeInTheDocument();
    const summary = screen.getByText("AI template assistant").closest("summary");
    const disclosure = summary?.closest("details");
    expect(disclosure).not.toHaveAttribute("open");

    fireEvent.click(summary as HTMLElement);
    expect(disclosure).toHaveAttribute("open");
    expect(screen.getByText("Assistant controls")).toBeInTheDocument();
  });
});
