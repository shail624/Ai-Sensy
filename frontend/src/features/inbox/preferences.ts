import { useCallback, useEffect, useMemo, useState } from "react";

import type { InboxFilters } from "@/features/inbox/types";

const CHANGE_EVENT = "wa-inbox-preferences";

export interface SavedInboxView {
  id: string;
  name: string;
  filters: InboxFilters;
}

interface InboxPreferences {
  pinned: string[];
  savedViews: SavedInboxView[];
}

const EMPTY: InboxPreferences = { pinned: [], savedViews: [] };

function storageKey(userId: string | undefined): string {
  return `wa.inbox.${userId ?? "anonymous"}`;
}

function read(userId: string | undefined): InboxPreferences {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey(userId)) ?? "null") as Partial<InboxPreferences> | null;
    return {
      pinned: Array.isArray(parsed?.pinned)
        ? parsed.pinned.filter((value): value is string => typeof value === "string")
        : [],
      savedViews: Array.isArray(parsed?.savedViews)
        ? parsed.savedViews.filter(
            (view): view is SavedInboxView =>
              typeof view?.id === "string" && typeof view?.name === "string" && Boolean(view.filters),
          )
        : [],
    };
  } catch {
    return EMPTY;
  }
}

function write(userId: string | undefined, value: InboxPreferences): void {
  localStorage.setItem(storageKey(userId), JSON.stringify(value));
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

/** Per-user presentation preferences. Operational conversation state always remains server-owned. */
export function useInboxPreferences(userId: string | undefined) {
  const [value, setValue] = useState<InboxPreferences>(() => read(userId));

  useEffect(() => {
    const sync = () => setValue(read(userId));
    sync();
    window.addEventListener(CHANGE_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [userId]);

  const togglePinned = useCallback((conversationId: string) => {
    const current = read(userId);
    write(userId, {
      ...current,
      pinned: current.pinned.includes(conversationId)
        ? current.pinned.filter((id) => id !== conversationId)
        : [conversationId, ...current.pinned],
    });
  }, [userId]);

  const saveView = useCallback((name: string, filters: InboxFilters) => {
    const current = read(userId);
    const id = `${Date.now()}`;
    write(userId, { ...current, savedViews: [...current.savedViews, { id, name, filters }] });
  }, [userId]);

  const deleteView = useCallback((id: string) => {
    const current = read(userId);
    write(userId, { ...current, savedViews: current.savedViews.filter((view) => view.id !== id) });
  }, [userId]);

  return useMemo(
    () => ({ ...value, togglePinned, saveView, deleteView }),
    [deleteView, saveView, togglePinned, value],
  );
}
