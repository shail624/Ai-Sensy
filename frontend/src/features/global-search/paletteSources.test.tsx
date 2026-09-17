import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * What the command palette can find.
 *
 * It already indexed contacts, campaigns, templates, numbers, users, tasks, media and
 * conversations. Segments, tags and reactivation cases were the org-wide records it did not,
 * which for this platform means the palette could not find the thing the business is *about*.
 */

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  asked: [] as string[],
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: state.permissions, is_superuser: false },
    hasPermission: (code: string) => state.permissions.includes(code),
    login: vi.fn(),
    logout: vi.fn(),
  }),
  useHasPermission: (code: string) => state.permissions.includes(code),
}));

vi.mock("@/lib/workspace", () => ({
  useWorkspacePreferences: () => ({
    favorites: [] as string[],
    recents: [] as { label: string; path: string }[],
    toggleFavorite: vi.fn(),
    recordRecent: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    GET: async (path: string) => {
      state.asked.push(path);
      if (path === "/api/v1/segments") {
        return {
          data: [
            {
              id: "sg1",
              name: "Sept winback base",
              description: "Prepaid, dormant 90 days",
              rules: [{ group_index: 0 }],
            },
          ],
        };
      }
      if (path === "/api/v1/tags") {
        return { data: [{ id: "tg1", name: "winback-sept", usage_count: 412 }] };
      }
      if (path === "/api/v1/reactivation-pipeline") {
        return {
          data: {
            data: [
              {
                id: "rc1",
                contact_id: "c9",
                contact_name: "Asha Mehta",
                stage: "interested",
                previous_vi_number: "+919990000001",
              },
            ],
          },
        };
      }
      return { data: { data: [] } };
    },
    POST: async () => ({ data: { data: [] } }),
  },
}));

vi.mock("@/features/inbox/api", () => ({ toListQuery: () => ({}) }));

import { CommandPalette } from "@/features/global-search/CommandPalette";

function withProviders(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

async function search(term: string) {
  withProviders(<CommandPalette open onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Search the workspace"), { target: { value: term } });
}

beforeEach(() => {
  state.permissions = [];
  state.asked = [];
});

describe("what the palette can find", () => {
  it("says what it searches, and the list is not stale", () => {
    // The placeholder named five sources and the palette now reaches eight. A promise on the
    // control itself ages the same way a contract description does.
    state.permissions = [];
    withProviders(<CommandPalette open onClose={vi.fn()} />);

    const placeholder = screen
      .getByLabelText("Search the workspace")
      .getAttribute("placeholder");
    expect(placeholder).toMatch(/segments/i);
    expect(placeholder).toMatch(/tags/i);
    expect(placeholder).toMatch(/cases/i);
  });

  it("finds a segment by name", async () => {
    state.permissions = ["segments:read"];
    await search("winback");

    await waitFor(() => expect(screen.getByText("Sept winback base")).toBeInTheDocument());
    expect(screen.getByText("Segments")).toBeInTheDocument();
  });

  it("finds a tag, and says how many contacts carry it", async () => {
    // A tag nobody uses looks identical to one on half the roster without the count.
    state.permissions = ["contacts:read"];
    await search("winback");

    await waitFor(() => expect(screen.getByText("winback-sept")).toBeInTheDocument());
    expect(screen.getByText("412 contacts")).toBeInTheDocument();
  });

  it("finds a reactivation case by the customer on it", async () => {
    // The record this whole platform exists to move, and the palette could not reach it.
    state.permissions = ["reactivation:read"];
    await search("asha");

    await waitFor(() => expect(screen.getByText("Asha Mehta")).toBeInTheDocument());
    expect(screen.getByText(/interested/)).toBeInTheDocument();
  });

  it("asks for nothing the signed-in user may not read", async () => {
    // Permission is checked before the request, not after the results come back.
    state.permissions = [];
    await search("winback");

    await waitFor(() => expect(state.asked).not.toContain("/api/v1/segments"));
    expect(state.asked).not.toContain("/api/v1/tags");
    expect(state.asked).not.toContain("/api/v1/reactivation-pipeline");
  });
});
