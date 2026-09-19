import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkspacePreferences } from "@/lib/workspace/preferences";

const get = vi.hoisted(() => vi.fn());
const put = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({ api: { GET: get, PUT: put } }));

const USER = "u1";
const STORAGE = `wa.workspace.${USER}`;

let client: QueryClient;
function wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function render() {
  return renderHook(() => useWorkspacePreferences(USER), { wrapper });
}

/** What the server currently holds for this user. */
function serverHas(preferences: Record<string, unknown>) {
  get.mockResolvedValue({ data: { preferences } });
}

beforeEach(() => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  localStorage.clear();
  get.mockReset();
  put.mockReset().mockResolvedValue({ data: {} });
});

describe("workspace favourites", () => {
  it("prefers the server's list over whatever this browser cached", async () => {
    localStorage.setItem(STORAGE, JSON.stringify({ favorites: ["/stale"], recents: [] }));
    serverHas({ workspace_favorites: ["/templates", "/contacts"] });

    const { result } = render();

    await waitFor(() => expect(result.current.favorites).toEqual(["/templates", "/contacts"]));
  });

  it("carries pre-existing browser favourites up on the first server read that lacks them", async () => {
    // Nobody should lose the favourites they starred before these became server-owned.
    localStorage.setItem(STORAGE, JSON.stringify({ favorites: ["/templates"], recents: [] }));
    serverHas({ theme: "dark" });

    render();

    await waitFor(() =>
      expect(put).toHaveBeenCalledWith("/api/v1/users/me/preferences", {
        body: { preferences: { theme: "dark", workspace_favorites: ["/templates"] } },
      }),
    );
  });

  it("treats a stored empty list as an answer, not as missing", async () => {
    // The subtle one: "starred nothing" must survive. If absent and empty were conflated, signing
    // in on an old device would resurrect favourites the user had deliberately cleared.
    localStorage.setItem(STORAGE, JSON.stringify({ favorites: ["/stale"], recents: [] }));
    serverHas({ workspace_favorites: [] });

    const { result } = render();

    await waitFor(() => expect(result.current.favorites).toEqual([]));
    expect(put).not.toHaveBeenCalled();
  });

  it("falls back to the cached list when the server cannot be read", async () => {
    // Degrading to "what this device last saw" is recoverable; degrading to empty looks to the
    // operator like their favourites were deleted.
    localStorage.setItem(STORAGE, JSON.stringify({ favorites: ["/templates"], recents: [] }));
    get.mockRejectedValue(new Error("offline"));

    const { result } = render();

    await waitFor(() => expect(result.current.favorites).toEqual(["/templates"]));
  });

  it("persists a toggle to the server and reflects it immediately", async () => {
    serverHas({ workspace_favorites: ["/templates"] });
    const { result } = render();
    await waitFor(() => expect(result.current.favorites).toEqual(["/templates"]));

    await act(async () => result.current.toggleFavorite("/contacts"));

    expect(put).toHaveBeenCalledWith("/api/v1/users/me/preferences", {
      body: { preferences: { workspace_favorites: ["/templates", "/contacts"] } },
    });
    expect(JSON.parse(localStorage.getItem(STORAGE)!).favorites).toEqual([
      "/templates",
      "/contacts",
    ]);
  });

  it("removes a favourite the second time it is toggled", async () => {
    serverHas({ workspace_favorites: ["/templates", "/contacts"] });
    const { result } = render();
    await waitFor(() => expect(result.current.favorites).toHaveLength(2));

    await act(async () => result.current.toggleFavorite("/templates"));

    expect(put).toHaveBeenCalledWith("/api/v1/users/me/preferences", {
      body: { preferences: { workspace_favorites: ["/contacts"] } },
    });
  });
});

describe("workspace recents", () => {
  it("stays in this browser and is never sent to the server", async () => {
    // Recents record what was opened *here*. Syncing them would let a phone reorder a desktop.
    serverHas({ workspace_favorites: [] });
    const { result } = render();
    await waitFor(() => expect(result.current.favorites).toEqual([]));

    await act(async () => result.current.recordRecent({ label: "Acme", path: "/contacts/1" }));

    expect(result.current.recents.map((r) => r.path)).toEqual(["/contacts/1"]);
    expect(put).not.toHaveBeenCalled();
  });
});
