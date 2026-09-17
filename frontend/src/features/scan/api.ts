import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { ReachabilityPage, Verdict } from "@/features/scan/types";

export const scanKeys = {
  all: ["scan"] as const,
  reachability: (verdict: string, q: string) => ["scan", "reachability", verdict, q] as const,
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
