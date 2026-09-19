import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

const CHANGE_EVENT = "wa-workspace-preferences";
const MAX_RECENTS = 8;

/**
 * The key favourites occupy inside the per-user preferences document. The contract stores a free
 * object, so this namespaces our slice away from anyone else's.
 */
const FAVORITES_KEY = "workspace_favorites";

export const workspaceKeys = {
  preferences: ["users", "me", "preferences"] as const,
};

export interface RecentItem {
  label: string;
  path: string;
  viewedAt: string;
}
interface WorkspacePreferences {
  favorites: string[];
  recents: RecentItem[];
}

const EMPTY: WorkspacePreferences = { favorites: [], recents: [] };

function storageKey(userId: string | undefined): string {
  return `wa.workspace.${userId ?? "anonymous"}`;
}

function read(userId: string | undefined): WorkspacePreferences {
  if (typeof localStorage === "undefined") return EMPTY;
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey(userId)) ?? "null") as Partial<WorkspacePreferences> | null;
    return {
      favorites: Array.isArray(parsed?.favorites)
        ? parsed.favorites.filter((value): value is string => typeof value === "string")
        : [],
      recents: Array.isArray(parsed?.recents)
        ? parsed.recents.filter(
            (value): value is RecentItem =>
              typeof value?.label === "string" &&
              typeof value?.path === "string" &&
              typeof value?.viewedAt === "string",
          )
        : [],
    };
  } catch {
    return EMPTY;
  }
}

function write(userId: string | undefined, value: WorkspacePreferences): void {
  localStorage.setItem(storageKey(userId), JSON.stringify(value));
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

function sameOrder(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function favoritesFrom(preferences: Record<string, unknown> | undefined): string[] | undefined {
  const stored = preferences?.[FAVORITES_KEY];
  if (!Array.isArray(stored)) return undefined;
  return stored.filter((value): value is string => typeof value === "string");
}

/**
 * Per-user workspace preferences: navigation favourites and recently visited records.
 *
 * Favourites are server-owned, so an agent who stars a destination finds it again on another
 * machine. Recents deliberately stay in this browser: they record what was opened *here*, and
 * syncing them would let a phone reorder a desktop's list.
 *
 * The browser copy of favourites is kept as a cache, not a second source of truth. It renders
 * immediately on a cold load and stands in if the read fails, so a network problem degrades the
 * list to "what this device last saw" rather than to empty — the one outcome that would look like
 * the user's favourites had been deleted.
 */
export function useWorkspacePreferences(userId: string | undefined) {
  const [local, setLocal] = useState<WorkspacePreferences>(() => read(userId));
  const queryClient = useQueryClient();

  useEffect(() => {
    setLocal(read(userId));
    const sync = () => setLocal(read(userId));
    window.addEventListener(CHANGE_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [userId]);

  const stored = useQuery({
    queryKey: workspaceKeys.preferences,
    queryFn: async (): Promise<Record<string, unknown>> =>
      unwrap(await api.GET("/api/v1/users/me/preferences")).preferences,
    enabled: Boolean(userId),
    staleTime: 5 * 60_000,
  });

  const serverFavorites = favoritesFrom(stored.data);

  const save = useMutation({
    mutationFn: async (favorites: string[]): Promise<string[]> => {
      await api.PUT("/api/v1/users/me/preferences", {
        body: { preferences: { ...(stored.data ?? {}), [FAVORITES_KEY]: favorites } },
      });
      return favorites;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: workspaceKeys.preferences }),
  });

  // A user who had favourites before this became server-owned keeps them: the first read that
  // comes back without the key adopts whatever this browser holds. Absent and empty are different
  // — an empty stored list means "starred nothing", and must not be overwritten from a stale
  // device.
  useEffect(() => {
    if (!userId || !stored.isSuccess || serverFavorites !== undefined) return;
    const carried = read(userId).favorites;
    if (carried.length > 0) save.mutate(carried);
    // `save` is intentionally not a dependency: including the mutation object re-runs this on
    // every render it produces, which would re-send the same seed repeatedly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, stored.isSuccess, serverFavorites]);

  const favorites = serverFavorites ?? local.favorites;

  // Keep the cache aligned with the server so the next cold load starts from the truth — but
  // not while a save is in flight, when the last read is by definition older than what the
  // user just did. Aligning then reverts the star under their cursor and restores it a moment
  // later.
  const saving = save.isPending;
  useEffect(() => {
    if (serverFavorites === undefined || saving) return;
    const current = read(userId);
    if (sameOrder(current.favorites, serverFavorites)) return;
    write(userId, { ...current, favorites: serverFavorites });
  }, [saving, serverFavorites, userId]);

  const toggleFavorite = useCallback(
    (path: string) => {
      const base = favoritesFrom(stored.data) ?? read(userId).favorites;
      const next = base.includes(path)
        ? base.filter((item) => item !== path)
        : [...base, path];
      // Write through the cache first so the star reacts at once, then persist.
      write(userId, { ...read(userId), favorites: next });
      save.mutate(next);
    },
    [save, stored.data, userId],
  );

  const recordRecent = useCallback(
    (item: Omit<RecentItem, "viewedAt">) => {
      const current = read(userId);
      const recents = [
        { ...item, viewedAt: new Date().toISOString() },
        ...current.recents.filter((recent) => recent.path !== item.path),
      ].slice(0, MAX_RECENTS);
      write(userId, { ...current, recents });
    },
    [userId],
  );

  return useMemo(
    () => ({ favorites, recents: local.recents, toggleFavorite, recordRecent }),
    [favorites, local.recents, recordRecent, toggleFavorite],
  );
}
