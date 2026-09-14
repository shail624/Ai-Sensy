import type {
  Job,
  JobListQuery,
  JobSort,
  QueueHealth,
  Worker,
} from "@/features/operations/types";
import { isWorkerStale } from "@/features/operations/types";

/** Rows per page for the client-side job list (see `useJobs` for why paging lives here). */
export const PAGE_SIZE = 25;

/** How long a job ran, in milliseconds, or `null` while it has not finished (or never started). */
export function durationMs(job: Job): number | null {
  if (!job.started_at || !job.finished_at) return null;
  const started = Date.parse(job.started_at);
  const finished = Date.parse(job.finished_at);
  if (Number.isNaN(started) || Number.isNaN(finished)) return null;
  return Math.max(0, finished - started);
}

/** How long a job waited before a worker picked it up, or `null` while it is still waiting. */
export function queuedMs(job: Job): number | null {
  if (!job.started_at) return null;
  const created = Date.parse(job.created_at);
  const started = Date.parse(job.started_at);
  if (Number.isNaN(created) || Number.isNaN(started)) return null;
  return Math.max(0, started - created);
}

const JOB_COMPARATORS: Record<JobSort, (a: Job, b: Job) => number> = {
  "-created_at": (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  created_at: (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
  "-attempts": (a, b) => b.attempts - a.attempts,
  // Unfinished jobs sort last: no duration yet is not "instant".
  duration: (a, b) => (durationMs(b) ?? -1) - (durationMs(a) ?? -1),
};

/**
 * Matches the task name, the queue, the failure text or the job id.
 *
 * The error text is searchable on purpose: an operator chasing an incident usually has a message
 * or an exception name to go on rather than a task name.
 */
export function matchesJob(job: Job, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return [job.task_name, job.queue, job.error_detail, job.ref_type]
    .filter((value): value is string => typeof value === "string")
    .some((value) => value.toLowerCase().includes(needle)) || job.id.toLowerCase().startsWith(needle);
}

export function filterJobs(jobs: Job[], query: JobListQuery): Job[] {
  return jobs.filter(
    (job) =>
      matchesJob(job, query.q) &&
      (query.status === "" || job.status === query.status) &&
      (query.queue === "" || job.queue === query.queue),
  );
}

export interface JobPage {
  rows: Job[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, in that order, so the page numbers describe the filtered set. */
export function selectJobPage(jobs: Job[], query: JobListQuery): JobPage {
  const matched = [...filterJobs(jobs, query)].sort(JOB_COMPARATORS[query.sort]);
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * PAGE_SIZE;
  return { rows: matched.slice(start, start + PAGE_SIZE), total: matched.length, totalPages, page };
}

/** Queue names present among the loaded jobs, so the filter offers only what it can match. */
export function jobQueues(jobs: Job[]): string[] {
  return [...new Set(jobs.map((job) => job.queue).filter((q): q is string => Boolean(q)))].sort();
}

export interface JobSummary {
  total: number;
  running: number;
  queued: number;
  failed: number;
  retrying: number;
  /** Jobs that took more than one attempt to get where they are. */
  retried: number;
}

export function jobSummary(jobs: Job[]): JobSummary {
  return {
    total: jobs.length,
    running: jobs.filter((job) => job.status === "started").length,
    queued: jobs.filter((job) => job.status === "queued").length,
    failed: jobs.filter((job) => job.status === "failure").length,
    retrying: jobs.filter((job) => job.status === "retry").length,
    retried: jobs.filter((job) => job.attempts > 1).length,
  };
}

// --- Queues ---------------------------------------------------------------------------------------

export interface QueueActivity {
  /** Jobs in this queue that a worker is running, among those loaded. */
  running: number;
  /** Jobs in this queue that failed, among those loaded. */
  failed: number;
  /** Jobs in this queue waiting to be retried, among those loaded. */
  retrying: number;
  /** Total retry attempts recorded across this queue's loaded jobs. */
  retryAttempts: number;
}

/**
 * Per-queue activity, derived from the loaded jobs.
 *
 * The `/queues` endpoint reports **backlog depth and worker coverage only** — it has no counters
 * for running, failed or retried work. So these figures come from the job page instead, which
 * makes them a sample rather than a total. Every surface that shows them says so; presenting them
 * as queue totals would be a quiet lie about how much has failed.
 */
export function queueActivity(jobs: Job[], queueName: string): QueueActivity {
  const mine = jobs.filter((job) => job.queue === queueName);
  return {
    running: mine.filter((job) => job.status === "started").length,
    failed: mine.filter((job) => job.status === "failure").length,
    retrying: mine.filter((job) => job.status === "retry").length,
    retryAttempts: mine.reduce((total, job) => total + Math.max(0, job.attempts - 1), 0),
  };
}

/** The live workers consuming a queue — worker assignment, straight from the heartbeat registry. */
export function workersForQueue(workers: Worker[], queueName: string): Worker[] {
  return workers.filter((worker) => worker.queues.includes(queueName));
}

/**
 * Queues ordered by what needs attention: uncovered backlog first, then depth, then priority.
 *
 * A queue with work and no worker is the one failure mode that silently stops the platform, so it
 * sorts above everything regardless of how deep it is.
 */
export function sortQueuesByAttention(queues: QueueHealth[]): QueueHealth[] {
  return [...queues].sort((a, b) => {
    const aStuck = a.depth > 0 && a.workers === 0;
    const bStuck = b.depth > 0 && b.workers === 0;
    if (aStuck !== bStuck) return aStuck ? -1 : 1;
    if (a.depth !== b.depth) return b.depth - a.depth;
    return a.priority - b.priority;
  });
}

/** A queue holding work that nothing is consuming — the state worth alerting on. */
export function isStalled(queue: QueueHealth): boolean {
  return queue.depth > 0 && queue.workers === 0;
}

export interface FleetSummary {
  queues: number;
  /** Total pending work across every declared queue. */
  depth: number;
  workers: number;
  staleWorkers: number;
  /** Tasks the live workers say they are running right now. */
  activeTasks: number;
  stalledQueues: number;
}

export function fleetSummary(
  queues: QueueHealth[],
  workers: Worker[],
  now: number = Date.now(),
): FleetSummary {
  return {
    queues: queues.length,
    depth: queues.reduce((total, queue) => total + queue.depth, 0),
    workers: workers.length,
    staleWorkers: workers.filter((worker) => isWorkerStale(worker, now)).length,
    activeTasks: workers.reduce((total, worker) => total + worker.active_tasks, 0),
    stalledQueues: queues.filter(isStalled).length,
  };
}
