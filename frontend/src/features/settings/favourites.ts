import { useCallback, useState } from "react";

function read(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

/**
 * Items the user starred, kept in this browser — a personal shortcut that sorts favourites first,
 * not shared team data.
 */
export function useFavouriteIds(key: string): [Set<string>, (id: string) => void] {
  const [ids, setIds] = useState<Set<string>>(() => read(key));
  const toggle = useCallback(
    (id: string) => {
      setIds((current) => {
        const next = new Set(current);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        try {
          localStorage.setItem(key, JSON.stringify([...next]));
        } catch {
          // Storage blocked: the star still works for this visit.
        }
        return next;
      });
    },
    [key],
  );
  return [ids, toggle];
}
