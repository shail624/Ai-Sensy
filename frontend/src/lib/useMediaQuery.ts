import { useCallback, useSyncExternalStore } from "react";

/**
 * Tailwind's `md` breakpoint is 768px, and Doc 05 DS-11/DS-14 put the compact (phone) layout
 * *below* it — tables reflow to stacked cards, filters move into a bottom sheet.
 */
export const COMPACT_QUERY = "(max-width: 767.98px)";

/**
 * Subscribes to a CSS media query. Used where the compact layout is a different tree rather than
 * different styling, so only one of the two is ever mounted (no duplicated rows in the DOM or the
 * accessibility tree). Where `matchMedia` is unavailable the query reads `false`.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (typeof window === "undefined" || !window.matchMedia) return () => undefined;
      const media = window.matchMedia(query);
      media.addEventListener("change", onStoreChange);
      // Belt and braces: a viewport change always fires `resize`, and re-reading the snapshot is
      // free when the answer has not changed (the store compares before re-rendering).
      window.addEventListener("resize", onStoreChange);
      return () => {
        media.removeEventListener("change", onStoreChange);
        window.removeEventListener("resize", onStoreChange);
      };
    },
    [query],
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia(query).matches;
  }, [query]);

  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

/** True on phone-width viewports (below `md`). */
export function useIsCompact(): boolean {
  return useMediaQuery(COMPACT_QUERY);
}
