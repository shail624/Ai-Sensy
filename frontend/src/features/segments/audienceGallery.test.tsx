import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AudiencePresetGallery } from "@/features/segments/AudiencePresetGallery";
import type { Segment } from "@/features/segments/types";

/**
 * Starting points on the new-segment page.
 *
 * Every segment is visible to the whole organization and any of them could always be copied from
 * the list's Duplicate action. What was missing was that somebody building their first audience
 * never saw them: the gallery offered the built-in recipes and nothing the team itself had
 * written, so a colleague's work was discoverable only if you already knew where to look.
 */

const state = vi.hoisted(() => ({
  permissions: ["segments:write"] as string[],
  segments: [] as Segment[],
}));

vi.mock("@/features/segments/api", () => ({
  useHasPermission: (code: string) => state.permissions.includes(code),
  useSegments: () => ({ data: state.segments, isPending: false }),
}));

function segment(overrides: Partial<Segment> = {}): Segment {
  return {
    id: "s1",
    type: "segment",
    name: "Sept winback base",
    description: "Prepaid, dormant 90 days, reachable",
    match_type: "all",
    is_dynamic: true,
    rules: [
      { group_index: 0, field_source: "scan", field_key: "reachability", operator: "eq", value: "reachable" },
    ],
    cached_count: 120,
    last_evaluated_at: null,
    created_at: "2026-09-10T00:00:00Z",
    updated_at: "2026-09-10T00:00:00Z",
    ...overrides,
  } as unknown as Segment;
}

function withProviders(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  state.permissions = ["segments:write"];
  state.segments = [];
});

describe("starting from the team's own audiences", () => {
  it("says nothing about them when the team has built none", () => {
    // A heading over an empty row would read as something broken rather than something unused.
    withProviders(<AudiencePresetGallery />);

    expect(screen.queryByText(/Start from your team/i)).not.toBeInTheDocument();
  });

  it("offers the team's audiences beside the built-in ones", () => {
    state.segments = [segment()];

    withProviders(<AudiencePresetGallery />);

    expect(screen.getByText(/Start from your team/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Sept winback base/ })).toBeInTheDocument();
  });

  it("opens the editor as a copy, leaving the original alone", () => {
    // The same `duplicateOf` state the list's Duplicate action already uses, so this adds an entry
    // point and not a second copy path.
    state.segments = [segment()];

    withProviders(<AudiencePresetGallery />);

    expect(screen.getByRole("link", { name: /Sept winback base/ })).toHaveAttribute(
      "href",
      "/segments/new",
    );
    expect(screen.getByText(/A copy opens in the editor with a new name/i)).toBeInTheDocument();
  });

  it("shows the newest few rather than everything the team has ever built", () => {
    // Fifty audiences would bury the built-in recipes under a wall of the team's own history; the
    // rest are one link away in the list this page already shows.
    state.segments = Array.from({ length: 9 }, (_, index) =>
      segment({
        id: `s${index}`,
        name: `Audience ${index}`,
        created_at: `2026-09-${String(index + 1).padStart(2, "0")}T00:00:00Z`,
      }),
    );

    withProviders(<AudiencePresetGallery />);

    expect(screen.getByRole("link", { name: /Audience 8/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Audience 0/ })).not.toBeInTheDocument();
  });

  it("falls back to the condition count when a segment has no description", () => {
    state.segments = [segment({ description: null } as Partial<Segment>)];

    withProviders(<AudiencePresetGallery />);

    expect(screen.getByText("1 condition")).toBeInTheDocument();
  });

  it("offers nothing at all to somebody who cannot write segments", () => {
    state.permissions = [];
    state.segments = [segment()];

    withProviders(<AudiencePresetGallery />);

    expect(screen.queryByText(/Quick-start audiences/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Start from your team/i)).not.toBeInTheDocument();
  });
});
