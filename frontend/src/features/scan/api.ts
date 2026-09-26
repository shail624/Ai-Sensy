import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { ReachabilityCounts, ReachabilityPage, Verdict } from "@/features/scan/types";

export const scanKeys = {
  all: ["scan"] as const,
  reachability: (verdict: string, q: string) => ["scan", "reachability", verdict, q] as const,
  counts: (q: string) => ["scan", "reachability", "counts", q] as const,
};

/**
 * Which contacts WhatsApp has reached, refused, or never been asked about.
 *
 * Derived on the server from campaign delivery evidence — there is no lookup to call and nothing
 * is sent to produce it, so this is an ordinary read and is not polled.
 */
export function useReachability(verdict: Verdict | "" = "", q = "", enabled = true) {
  return useQuery({
    queryKey: scanKeys.reachability(verdict, q),
    queryFn: async (): Promise<ReachabilityPage> =>
      unwrap(
        await api.GET("/api/v1/scan/reachability", {
          params: { query: { ...(verdict ? { verdict } : {}), ...(q ? { q } : {}) } },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/**
 * The tallies, fetched separately from the rows.
 *
 * Not a style choice: a page reads fifty contacts, while counting every contact's state reads the
 * whole recipient ledger — 9ms against 425ms at 200,000 recipients. Asked together, the list waited
 * for the tallies. Asked apart, the list appears at once and the numbers arrive when they arrive.
 *
 * The search is passed through, so the two always describe the same population.
 */
export function useReachabilityCounts(q = "", enabled = true) {
  return useQuery({
    queryKey: scanKeys.counts(q),
    queryFn: async (): Promise<ReachabilityCounts> =>
      unwrap(
        await api.GET("/api/v1/scan/reachability/counts", {
          params: { query: q ? { q } : {} },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
  });
}
