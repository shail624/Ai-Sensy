import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  Job,
  JobsPage,
  QueuesSnapshot,
  WebhookDeadLetterPage,
  WebhookEventsPage,
} from "@/features/operations/types";
import { JOB_TERMINAL_STATUSES } from "@/features/operations/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const operationsKeys = {
  all: ["operations"] as const,
  jobs: ["operations", "jobs"] as const,
  job: (id: string) => ["operations", "jobs", id] as const,
  queues: ["operations", "queues"] as const,
  webhookEvents: (status: string) => ["operations", "webhook-events", status] as const,
  webhookDeadLetters: (status: string) => ["operations", "webhook-dlq", status] as const,
};

/** Queue depth moves by the second, so the monitor polls rather than waiting for a navigation. */
const QUEUE_POLL_MS = 10_000;
/** Job state moves more slowly than queue depth, and the list is heavier to fetch. */
const JOB_POLL_MS = 15_000;
/** Webhook traffic is the first thing checked when messages stop; keep it close to live. */
const WEBHOOK_POLL_MS = 15_000;

/**
 * Background jobs, newest first.
 *
 * `GET /jobs` is cursor-paginated. CORE-19 declared `limit` and `cursor` in the contract, so both
 * are now reachable from the generated client; the `filter[field][op]` grammar stays on the raw
 * request by design (Doc 04 §7.1), since it spans any field crossed with eleven operators. This
 * hook still asks for the **default page of 50** and the true `page.total`, with search, filtering,
 * sorting and paging running in the client over that page (`selectors.ts`) and the UI saying so
 * when `total` exceeds what it holds. Server-side paging here is a change worth making
 * deliberately, not a limitation of the contract any more.
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

/**
 * Inbound webhook deliveries, newest first.
 *
 * Polled for the same reason the job list is: this is the screen someone opens *while* messages
 * have stopped arriving, and one that only updates on reload cannot answer "is it still stuck".
 */
export function useWebhookEvents(status = "", enabled = true) {
  return useQuery({
    queryKey: operationsKeys.webhookEvents(status),
    queryFn: async (): Promise<WebhookEventsPage> =>
      unwrap(
        await api.GET("/api/v1/webhooks/events", {
          params: { query: status ? { status } : {} },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
    refetchInterval: enabled ? WEBHOOK_POLL_MS : false,
    refetchIntervalInBackground: false,
  });
}

/** Events whose retries are exhausted, with the error that stopped each one. */
export function useWebhookDeadLetters(status = "", enabled = true) {
  return useQuery({
    queryKey: operationsKeys.webhookDeadLetters(status),
    queryFn: async (): Promise<WebhookDeadLetterPage> =>
      unwrap(
        await api.GET("/api/v1/webhooks/dead-letter", {
          params: { query: status ? { status } : {} },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
    refetchInterval: enabled ? WEBHOOK_POLL_MS : false,
    refetchIntervalInBackground: false,
  });
}

/**
 * Put a parked event back through processing, or close it without doing so.
 *
 * Written out twice rather than shared behind a path template: the generated client types each
 * path separately, and the one thing worth keeping here is that these calls are checked against
 * the contract. A shared helper would have to cast that away.
 *
 * Both invalidate the whole operations key, because replaying changes the delivery list as well as
 * the queue — a screen showing the entry gone while the delivery it produced was still missing
 * would be worse than not refreshing at all.
 */
function useOperationsMutation<T>(mutationFn: (value: T) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => void client.invalidateQueries({ queryKey: operationsKeys.all }),
  });
}

export function useReplayDeadLetter() {
  return useOperationsMutation(async (entryId: string) =>
    unwrap(
      await api.POST("/api/v1/webhooks/dead-letter/{entry_id}/replay", {
        params: { path: { entry_id: entryId } },
      }),
    ),
  );
}

export function useDiscardDeadLetter() {
  return useOperationsMutation(async (entryId: string) =>
    unwrap(
      await api.POST("/api/v1/webhooks/dead-letter/{entry_id}/discard", {
        params: { path: { entry_id: entryId } },
      }),
    ),
  );
}
