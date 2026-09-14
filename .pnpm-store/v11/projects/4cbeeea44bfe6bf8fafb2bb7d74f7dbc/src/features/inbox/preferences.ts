import { useCallback, useEffect, useMemo, useState } from "react";

import type { InboxFilters } from "@/features/inbox/types";
import { usePreferences, useUpdatePreferences } from "@/features/settings/api";

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
    return parse(JSON.parse(localStorage.getItem(storageKey(userId)) ?? "null"));
  } catch {
    return EMPTY;
  }
}

function parse(value: unknown): InboxPreferences {
  const parsed = value && typeof value === "object" ? value as Partial<InboxPreferences> : null;
  return {
    pinned: Array.isArray(parsed?.pinned)
      ? parsed.pinned.filter((entry): entry is string => typeof entry === "string")
      : [],
    savedViews: Array.isArray(parsed?.savedViews)
      ? parsed.savedViews.filter(
          (view): view is SavedInboxView =>
            typeof view?.id === "string" && typeof view?.name === "string" && Boolean(view.filters),
        )
      : [],
  };
}

function write(userId: string | undefined, value: InboxPreferences): void {
  localStorage.setItem(storageKey(userId), JSON.stringify(value));
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

/** Per-user presentation preferences. Operational conversation state always remains server-owned. */
export function useInboxPreferences(userId: string | undefined) {
  const [value, setValue] = useState<InboxPreferences>(() => read(userId));
  const server = usePreferences();
  const update = useUpdatePreferences();
  const syncServer = update.mutate;

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

  // Phase 2 promotes custom inboxes and pins to the existing server preference store. Browser
  // storage remains an instant/offline cache and is migrated on the first signed-in read.
  useEffect(() => {
    if (!userId || !server.data) return;
    if (Object.hasOwn(server.data, "inbox_workspace")) {
      write(userId, parse(server.data.inbox_workspace));
      return;
    }
    const current = read(userId);
    if (current.pinned.length > 0 || current.savedViews.length > 0) {
      syncServer({ inbox_workspace: current });
    }
  }, [server.data, syncServer, userId]);

  const persist = useCallback((next: InboxPreferences) => {
    write(userId, next);
    if (userId) syncServer({ inbox_workspace: next });
  }, [syncServer, userId]);

  const togglePinned = useCallback((conversationId: string) => {
    const current = read(userId);
    persist({
      ...current,
      pinned: current.pinned.includes(conversationId)
        ? current.pinned.filter((id) => id !== conversationId)
        : [conversationId, ...current.pinned],
    });
  }, [persist, userId]);

  const saveView = useCallback((name: string, filters: InboxFilters) => {
    const current = read(userId);
    const id = `${Date.now()}`;
    persist({ ...current, savedViews: [...current.savedViews, { id, name, filters }] });
  }, [persist, userId]);

  const deleteView = useCallback((id: string) => {
    const current = read(userId);
    persist({ ...current, savedViews: current.savedViews.filter((view) => view.id !== id) });
  }, [persist, userId]);

  return useMemo(
    () => ({ ...value, togglePinned, saveView, deleteView }),
    [deleteView, saveView, togglePinned, value],
  );
}
