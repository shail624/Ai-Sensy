import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { Job, JobsPage, QueuesSnapshot } from "@/features/operations/types";
import { JOB_TERMINAL_STATUSES } from "@/features/operations/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const operationsKeys = {
  all: ["operations"] as const,
  jobs: ["operations", "jobs"] as const,
  job: (id: string) => ["operations", "jobs", id] as const,
  queues: ["operations", "queues"] as const,
};

/** Queue depth moves by the second, so the monitor polls rather than waiting for a navigation. */
const QUEUE_POLL_MS = 10_000;
/** Job state moves more slowly than queue depth, and the list is heavier to fetch. */
const JOB_POLL_MS = 15_000;

/**
 * Background jobs, newest first.
 *
 * `GET /jobs` is cursor-paginated and accepts `filter[status][eq]`, `filter[task_name][eq]`,
 * `filter[queue][eq]`, `limit` and `cursor` — but reads every one off `request.query_params`, so
 * none is declared in the contract or reachable from the generated client. It therefore answers
 * with its **default page of 50**, plus the true `page.total`. Search, filtering, sorting and
 * paging run in the client over that page (`selectors.ts`), and the UI says so when `total`
 * exceeds what it holds.
 *
 * Polled because this is a monitoring surface: a job list that only updates when you reload is not
 * telling you what the system is doing.
 */
export function useJobs(live = true) {
  return useQuery({
    queryKey: operationsKeys.jobs,
    queryFn: async (): Promise<JobsPage> => unwrap(await api.GET("/api/v1/jobs")),
    placeholderData: keepPreviousData,
    refetchInterval: live ? JOB_POLL_MS : false,
    refetchIntervalInBackground: false,
  });
}

/**
 * One job.
 *
 * Polling stops as soon as the job reaches a terminal state — its record never changes again, so
 * continuing would be a request per interval for a constant answer. The decision is made from the
 * response itself rather than from a caller-supplied flag, so a job that finishes while the page is
 * open settles on its own.
 */
export function useJob(jobId: string, enabled = true) {
  return useQuery({
    queryKey: operationsKeys.job(jobId),
    queryFn: async (): Promise<Job> =>
      unwrap(await api.GET("/api/v1/jobs/{job_id}", { params: { path: { job_id: jobId } } })),
    enabled: enabled && Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && JOB_TERMINAL_STATUSES.includes(status) ? false : JOB_POLL_MS;
    },
    refetchIntervalInBackground: false,
  });
}

/**
 * Queue depth and fleet health.
 *
 * Depth is read **live from the broker** — each Celery queue is a Redis list, so depth is its
 * length — rather than from a mirror table, because the broker is the source of truth for backlog
 * and a stale copy would be worse than none. Worker liveness comes from the heartbeat registry.
 */
export function useQueues(live = true) {
  return useQuery({
    queryKey: operationsKeys.queues,
    queryFn: async (): Promise<QueuesSnapshot> => unwrap(await api.GET("/api/v1/queues")),
    placeholderData: keepPreviousData,
    refetchInterval: live ? QUEUE_POLL_MS : false,
    refetchIntervalInBackground: false,
  });
}

/**
 * Cancel a job that has not finished.
 *
 * The server revokes the Celery task **without terminating it**: a worker already running the task
 * is not killed mid-write, it simply will not be handed the work again. So cancelling a `started`
 * job stops future attempts rather than the current one — which is the safe behaviour, and worth
 * saying plainly in the confirmation rather than implying an instant stop.
 *
 * A terminal job cannot be cancelled and the server answers 409.
 */
export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (jobId: string): Promise<Job> =>
      unwrap(
        await api.POST("/api/v1/jobs/{job_id}/cancel", {
          params: { path: { job_id: jobId } },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: operationsKeys.all });
    },
  });
}
