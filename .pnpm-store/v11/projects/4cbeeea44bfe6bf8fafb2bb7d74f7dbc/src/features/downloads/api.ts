import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { DownloadQuery, DownloadsPage } from "@/features/downloads/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export const downloadKeys = {
  all: ["downloads"] as const,
  list: (query: DownloadQuery) => ["downloads", "list", query] as const,
};

const ACTIVE_POLL_MS = 3_000;

/** Personal export history; active pages poll until no queued/preparing artifact remains. */
export function useDownloads(query: DownloadQuery) {
  return useQuery({
    queryKey: downloadKeys.list(query),
    queryFn: async (): Promise<DownloadsPage> =>
      unwrap(
        await api.GET("/api/v1/downloads", {
          params: {
            query: {
              category: query.category,
              status: query.status === "all" ? undefined : query.status,
              limit: 25,
              cursor: query.cursor,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: (result) =>
      result.state.data?.data.some((item) =>
        item.status === "pending" || item.status === "processing"
      )
        ? ACTIVE_POLL_MS
        : false,
  });
}
