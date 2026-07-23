import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
// The administration feature owns the shared list footer; importing it keeps one implementation of
// "how these lists page, and what they say about what they hold".
import { AdminPagination } from "@/features/admin";
import { apiErrorMessage, useJobs, useQueues } from "@/features/operations/api";
import {
  AttemptsChip,
  JobStatusChip,
  PriorityChip,
  QueueChip,
} from "@/features/operations/OperationsBadges";
import { JobActions } from "@/features/operations/JobActions";
import { durationMs, jobQueues, jobSummary, selectJobPage } from "@/features/operations/selectors";
import type { JobListQuery, JobSort } from "@/features/operations/types";
import {
  DEFAULT_JOB_QUERY,
  JOB_STATUS_LABELS,
  JOB_STATUSES,
} from "@/features/operations/types";
// Elapsed time, not playback time: the analytics formatter degrades to milliseconds, which matters
// here because most tasks finish in well under a second. `lib/format`'s `formatDuration` is `m:ss`
// for media and would render every fast job as "0:00".
import { formatDuration } from "@/features/analytics/format";
import { formatAge, formatCount } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORTS: JobSort[] = ["-created_at", "created_at", "-attempts", "duration"];

const SORT_LABELS: Record<JobSort, string> = {
  "-created_at": "Newest",
  created_at: "Oldest",
  "-attempts": "Most attempts",
  duration: "Longest running",
};

function readQuery(params: URLSearchParams): JobListQuery {
  const status = params.get("status") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? "",
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    status: JOB_STATUSES.includes(status) ? status : "",
    queue: params.get("queue") ?? "",
    sort: SORTS.includes(sort as JobSort) ? (sort as JobSort) : DEFAULT_JOB_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: JobListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (query.queue) params.set("queue", query.queue);
  if (query.sort !== DEFAULT_JOB_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * The jobs dashboard (Doc 05 B11.8) — what the background fleet has been asked to do and how it
 * went.
 *
 * The list polls, because a monitoring surface that only updates on reload is not monitoring
 * anything. Filtering runs client-side over the endpoint's default page of 50 (`api.ts` explains
 * why), and the footer states plainly when more jobs exist than are loaded — an operator hunting a
 * failure needs to know they may be looking at the wrong 50.
 */
export function JobList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);

  const jobs = useJobs();
  // Priority lives on the queue, not the job, so the queue snapshot is what makes a job row able to
  // show how urgent its work was.
  const queues = useQueues();

  const rows = useMemo(() => jobs.data?.data ?? [], [jobs.data]);
  const page = useMemo(() => selectJobPage(rows, query), [rows, query]);
  const summary = useMemo(() => jobSummary(rows), [rows]);
  const queueNames = useMemo(() => jobQueues(rows), [rows]);
  const total = jobs.data?.page.total ?? rows.length;

  const priorityOf = useMemo(() => {
    const byName = new Map((queues.data?.queues ?? []).map((queue) => [queue.name, queue.priority]));
    return (name: string | null) => (name === null ? undefined : byName.get(name));
  }, [queues.data]);

  const isFiltered = query.q !== "" || query.status !== "" || query.queue !== "";

  function apply(next: Partial<JobListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next, page: 1 }));
  }

  if (jobs.isLoading) return <Spinner label="Loading jobs…" />;

  if (jobs.isError) {
    return <ErrorState message={apiErrorMessage(jobs.error)} onRetry={() => void jobs.refetch()} />;
  }

  return (
    <>
      {rows.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.running)} running · {formatCount(summary.queued)} queued ·{" "}
          {formatCount(summary.failed)} failed · {formatCount(summary.retrying)} retrying
          {summary.retried > 0 ? ` · ${formatCount(summary.retried)} needed more than one attempt` : ""}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
            <label htmlFor="jobs-search" className="text-xs font-medium text-text-secondary">
              Search
            </label>
            <input
              id="jobs-search"
              type="search"
              value={query.q}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Task, queue or error…"
              className={FIELD_CLASS}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="jobs-status" className="text-xs font-medium text-text-secondary">
              Status
            </label>
            <select
              id="jobs-status"
              value={query.status}
              onChange={(event) => apply({ status: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All statuses</option>
              {JOB_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {JOB_STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="jobs-queue" className="text-xs font-medium text-text-secondary">
              Queue
            </label>
            <select
              id="jobs-queue"
              value={query.queue}
              onChange={(event) => apply({ queue: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All queues</option>
              {queueNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="jobs-sort" className="text-xs font-medium text-text-secondary">
              Sort
            </label>
            <select
              id="jobs-sort"
              value={query.sort}
              onChange={(event) => apply({ sort: event.target.value as JobSort })}
              className={FIELD_CLASS}
            >
              {SORTS.map((sort) => (
                <option key={sort} value={sort}>
                  {SORT_LABELS[sort]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void jobs.refetch()}
          disabled={jobs.isFetching}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50"
        >
          {jobs.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          title="No jobs recorded"
          description="Background work appears here as soon as anything is queued — imports, exports, campaign sends, syncs and rollups."
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No jobs match these filters"
          description="Try a different status, queue or search term. Only the 50 most recent jobs are loaded, so an older job may not be among them."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Task</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Queue</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Attempts</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Duration</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Created</th>
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((job) => {
                  const ran = durationMs(job);
                  const priority = priorityOf(job.queue);
                  return (
                    <tr key={job.id} className="border-b border-border last:border-0 hover:bg-hover">
                      <td className="px-3 py-2">
                        <Link
                          to={`/operations/jobs/${job.id}`}
                          className="break-all font-mono text-xs font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                        >
                          {job.task_name}
                        </Link>
                        {job.error_detail ? (
                          <p className="mt-1 truncate text-xs text-danger" title={job.error_detail}>
                            {job.error_detail}
                          </p>
                        ) : null}
                        <div className="mt-1 flex flex-wrap gap-1 lg:hidden">
                          {job.queue ? <QueueChip name={job.queue} /> : null}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <JobStatusChip value={job.status} />
                      </td>
                      <td className="hidden px-3 py-2 lg:table-cell">
                        <div className="flex flex-wrap items-center gap-1">
                          {job.queue ? <QueueChip name={job.queue} /> : <span className="text-text-disabled">—</span>}
                          {priority !== undefined ? <PriorityChip priority={priority} /> : null}
                        </div>
                      </td>
                      <td className="hidden px-3 py-2 xl:table-cell">
                        <AttemptsChip attempts={job.attempts} />
                      </td>
                      <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                        {ran === null ? "—" : formatDuration(ran / 1000)}
                      </td>
                      <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                        {formatAge(job.created_at)}
                      </td>
                      <td className="px-3 py-2">
                        <JobActions job={job} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <AdminPagination
            page={page.page}
            totalPages={page.totalPages}
            total={page.total}
            noun="job"
            filtered={isFiltered}
            onGoTo={(next) => setSearchParams(writeQuery({ ...query, page: next }))}
            truncatedTo={{ loaded: rows.length, available: total }}
          />
        </>
      )}
    </>
  );
}
