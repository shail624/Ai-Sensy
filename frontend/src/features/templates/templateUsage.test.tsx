import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { TemplateTable } from "@/features/templates/TemplateTable";
import type { Template, TemplateUsage } from "@/features/templates/types";

vi.mock("@/features/templates/TemplateActions", () => ({
  TemplateActions: () => <span />,
}));

const template = {
  id: "t1",
  type: "template",
  waba_id: "w1",
  name: "reactivation_offer",
  language: "en",
  category: "marketing",
  status: "approved",
  quality_score: null,
  rejection_reason: null,
  components: [],
  variable_count: 0,
  has_media_header: false,
  is_sendable: true,
  last_synced_at: null,
  row_version: 1,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
} as unknown as Template;

function usage(overrides: Partial<TemplateUsage> = {}): Map<string, TemplateUsage> {
  return new Map([
    [
      "t1",
      {
        template_id: "t1",
        name: "reactivation_offer",
        language: "en",
        category: "marketing",
        status: "approved",
        campaigns: 2,
        recipients: 1200,
        delivered: 1080,
        failed: 120,
        delivery_rate: 0.9,
        last_used_at: "2026-09-10T00:00:00Z",
        ...overrides,
      } as TemplateUsage,
    ],
  ]);
}

function renderTable(rows?: Map<string, TemplateUsage>) {
  return render(
    <MemoryRouter>
      <TemplateTable templates={[template]} usage={rows} />
    </MemoryRouter>,
  );
}

describe("TemplateTable send history", () => {
  it("shows how many people a template reached and how many arrived", () => {
    renderTable(usage());

    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row).toHaveTextContent("1,200");
    expect(row).toHaveTextContent("90%");
  });

  it("says 'Never sent' instead of 0% for a template nobody has used", () => {
    // 0% reads as "everything failed" when nothing was tried, and those call for opposite actions.
    renderTable(usage({ campaigns: 0, recipients: 0, delivered: 0, failed: 0, delivery_rate: null }));

    expect(within(screen.getByRole("table")).getAllByRole("row")[1]).toHaveTextContent("Never sent");
  });

  it("shows a dash rather than a wrong number while the history is still loading", () => {
    renderTable(undefined);

    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row).not.toHaveTextContent("Never sent");
    expect(row).not.toHaveTextContent("0%");
  });
});
