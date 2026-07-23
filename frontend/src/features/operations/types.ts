import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Job = components["schemas"]["JobResponse"];
export type JobsPage = components["schemas"]["JobsPage"];
export type QueuesSnapshot = components["schemas"]["QueuesResponse"];
export type QueueHealth = components["schemas"]["QueueHealthResponse"];
export type Worker = components["schemas"]["WorkerResponse"];

/**
 * Job status — the six values `JOB_STATUSES` defines (Doc 03 §11.7).
 *
 * The contract types the field as `str`, so this is the **display vocabulary**, not an API type.
 * A value outside the list renders verbatim rather than being dropped.
 */
export const JOB_STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  started: "Running",
  success: "Succeeded",
  failure: "Failed",
  retry: "Retrying",
  revoked: "Cancelled",
};

export const JOB_STATUSES = Object.keys(JOB_STATUS_LABELS);

export const JOB_STATUS_EXPLANATIONS: Record<string, string> = {
  queued: "Accepted and waiting for a worker to pick it up.",
  started: "A worker is running it now.",
  success: "Finished and did what it was asked to do.",
  failure: "Gave up after exhausting its attempts. Its work did not complete.",
  retry: "An attempt failed and it is waiting to be attempted again.",
  revoked: "Cancelled by an operator before it finished.",
};

/** `JOB_TERMINAL_STATUSES` — nothing more will happen to a job in one of these. */
export const JOB_TERMINAL_STATUSES = ["success", "failure", "revoked"];

export function isTerminal(job: Job): boolean {
  return JOB_TERMINAL_STATUSES.includes(job.status);
}

/**
 * Only a non-terminal job can be cancelled — the server answers 409 otherwise, so the control is
 * not offered on a job that has already finished.
 */
export function isCancellable(job: Job): boolean {
  return !isTerminal(job);
}

/** A job that ran more than once has been retried, whatever its current status says. */
export function wasRetried(job: Job): boolean {
  return job.attempts > 1;
}

/**
 * Queue priority as the registry declares it: P0 is highest, P4 lowest (Doc 06 §2.3).
 *
 * Priority belongs to the **queue**, not the job — a job's urgency is entirely a function of which
 * queue it was routed to, which is why job rows show their queue's priority rather than one of
 * their own.
 */
export function priorityLabel(priority: number): string {
  return `P${priority}`;
}

export const PRIORITY_DESCRIPTIONS: Record<number, string> = {
  0: "Control and urgent work — nothing waits behind it.",
  1: "A user is waiting on this.",
  2: "Throughput work: campaign sends, retries, media.",
  3: "Batch work: imports, exports, rollups, template sync.",
  4: "Background maintenance and cleanup.",
};

/** A worker is considered live while its heartbeat is recent. */
export const WORKER_STALE_SECONDS = 90;

export function isWorkerStale(worker: Worker, now: number = Date.now()): boolean {
  if (!worker.last_seen_at) return true;
  const seen = Date.parse(worker.last_seen_at);
  return Number.isNaN(seen) || now - seen > WORKER_STALE_SECONDS * 1000;
}

// --- List query (client-side; see `api.ts` for why) ----------------------------------------------

export type JobSort = "-created_at" | "created_at" | "-attempts" | "duration";

export interface JobListQuery {
  q: string;
  status: string;
  queue: string;
  sort: JobSort;
  page: number;
}

export const DEFAULT_JOB_QUERY: JobListQuery = {
  q: "",
  status: "",
  queue: "",
  sort: "-created_at",
  page: 1,
};
