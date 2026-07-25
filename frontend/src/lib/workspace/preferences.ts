import { useCallback, useEffect, useMemo, useState } from "react";

const CHANGE_EVENT = "wa-workspace-preferences";
const MAX_RECENTS = 8;

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

/** Small, per-user browser preference layer for navigation favorites and recently visited records. */
export function useWorkspacePreferences(userId: string | undefined) {
  const [value, setValue] = useState<WorkspacePreferences>(() => read(userId));

  useEffect(() => {
    setValue(read(userId));
    const sync = () => setValue(read(userId));
    window.addEventListener(CHANGE_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [userId]);

  const toggleFavorite = useCallback(
    (path: string) => {
      const current = read(userId);
      const favorites = current.favorites.includes(path)
        ? current.favorites.filter((item) => item !== path)
        : [...current.favorites, path];
      write(userId, { ...current, favorites });
    },
    [userId],
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
    () => ({ ...value, toggleFavorite, recordRecent }),
    [recordRecent, toggleFavorite, value],
  );
}
