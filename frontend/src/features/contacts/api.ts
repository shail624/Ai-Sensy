import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { ContactsPage, SegmentRule } from "@/features/contacts/types";

export interface ContactSearchParams {
  rules: SegmentRule[];
  cursor: string | null;
  limit: number;
}

/**
 * The typed contacts list, via `POST /contacts/search` — the only contacts endpoint whose query is
 * in the OpenAPI contract (`GET /contacts` declares no parameters). Empty `rules` returns everyone,
 * cursor-paginated. `keepPreviousData` keeps the table stable while a new page/filter loads.
 */
export function useContactSearch(params: ContactSearchParams) {
  return useQuery({
    queryKey: ["contacts", "search", params],
    queryFn: async (): Promise<ContactsPage> =>
      unwrap(
        await api.POST("/api/v1/contacts/search", {
          body: {
            match_type: "all",
            rules: params.rules,
            limit: params.limit,
            cursor: params.cursor,
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
