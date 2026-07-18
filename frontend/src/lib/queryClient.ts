import { QueryClient } from "@tanstack/react-query";

// Shared TanStack Query client (Doc 05 — data fetching layer).
// Cache-first with sensible retry/staleness defaults; auth-aware retry logic
// (do not retry 401/403) is added with the API client in the auth step.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
