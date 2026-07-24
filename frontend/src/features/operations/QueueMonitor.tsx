import { useMemo } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useJobs, useQueues } from "@/features/operations/api";
import {
  DepthChip,
  PriorityChip,
  QueueChip,
  StalledChip,
  WorkerChip,
} from "@/features/operations/OperationsBadges";
import {
  fleetSummary,
  isStalled,
  queueActivity,
  sortQueuesByAttention,
  workersForQueue,
} from "@/features/operations/selectors";
import type { QueueHealth } from "@/features/operations/types";
import { formatAge, formatCount } from "@/lib/format";

/**
 * The queue monitor (Doc 05 B11.8) — backlog, worker coverage and fleet health.
 *
 * Depth and worker liveness come from `/queues`, which reads the broker and the heartbeat registry
 * live. Running, failed and retried counts do **not**: the endpoint has no counters for them, so
 * they are derived from the loaded job page and labelled as a sample. Presenting a sample as a
 * queue total would be a quiet lie about how much has failed.
 */
export function QueueMonitor(): JSX.Element {
  const queues = useQueues();
  const jobs = useJobs();

  const snapshot = queues.data;
  const loadedJobs = useMemo(() => jobs.data?.data ?? [], [jobs.data]);

  const ordered = useMemo(
    () => sortQueuesByAttention(snapshot?.queues ?? []),
    [snapshot?.queues],
  );
  const fleet = useMemo(
    () => fleetSummary(snapshot?.queues ?? [], snapshot?.workers ?? []),
    [snapshot],
  );

  if (queues.isLoading) return <Spinner label="Reading queue health…" />;

  if (queues.isError || !snapshot) {
    return (
      <ErrorState message={apiErrorMessage(queues.error)} onRetry={() => void queues.refetch()} />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-text-secondary">
          {formatCount(fleet.depth)} task{fleet.depth === 1 ? "" : "s"} waiting ·{" "}
          {formatCount(fleet.activeTasks)} running · {formatCount(fleet.workers)} worker
          {fleet.workers === 1 ? "" : "s"}
          {fleet.staleWorkers > 0 ? ` (${formatCount(fleet.staleWorkers)} stale)` : ""}
          {snapshot.dead_letter_parked > 0
            ? ` · ${formatCount(snapshot.dead_letter_parked)} parked in dead letter`
            : ""}
        </p>
        <button
          type="button"
          onClick={() => {
            void queues.refetch();
            void jobs.refetch();
          }}
          disabled={queues.isFetching}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50"
        >
          {queues.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {fleet.workers === 0 ? (
        <p role="alert" className="rounded-md border border-danger px-3 py-2 text-sm text-danger">
          No worker has reported a heartbeat. Nothing queued is being processed — check that the
          worker containers are running.
        </p>
      ) : fleet.stalledQueues > 0 ? (
        <p role="alert" className="rounded-md border border-danger px-3 py-2 text-sm text-danger">
          {formatCount(fleet.stalledQueues)} queue
          {fleet.stalledQueues === 1 ? " holds" : "s hold"} work that no live worker is consuming.
        </p>
      ) : null}

      {snapshot.dead_letter_parked > 0 ? (
        <p className="rounded-md border border-warning px-3 py-2 text-sm text-warning">
          {formatCount(snapshot.dead_letter_parked)} task
          {snapshot.dead_letter_parked === 1 ? " is" : "s are"} parked in the dead-letter queue.
          The platform exposes no endpoint to inspect or replay them, so they need attention from the
          server side.
        </p>
      ) : null}

      <Section title="Queues">
        {ordered.length === 0 ? (
          <EmptyState title="No queues declared" description="The queue registry is empty." />
        ) : (
          <>
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                  <tr>
                    <th scope="col" className="px-3 py-2">Queue</th>
                    <th scope="col" className="px-3 py-2">Pending</th>
                    <th scope="col" className="hidden px-3 py-2 md:table-cell">Workers</th>
                    <th scope="col" className="hidden px-3 py-2 lg:table-cell">Running</th>
                    <th scope="col" className="hidden px-3 py-2 lg:table-cell">Failed</th>
                    <th scope="col" className="hidden px-3 py-2 xl:table-cell">Retries</th>
                    <th scope="col" className="hidden px-3 py-2 xl:table-cell">On failure</th>
                  </tr>
                </thead>
                <tbody>
                  {ordered.map((queue) => (
                    <QueueRow
                      key={queue.name}
                      queue={queue}
                      workers={workersForQueue(snapshot.workers, queue.name)}
                      activity={queueActivity(loadedJobs, queue.name)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-2 text-xs text-text-disabled">
              Pending and worker coverage are read live from the broker. Running, failed and retry
              figures are counted from the most recent {formatCount(loadedJobs.length)} jobs — they
              are a sample of recent activity, not queue totals.
            </p>
          </>
        )}
      </Section>

      <Section title="Workers">
        {snapshot.workers.length === 0 ? (
          <EmptyState
            title="No live workers"
            description="Workers report a heartbeat while they run. None has reported, so nothing is consuming any queue."
          />
        ) : (
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Worker</th>
                  <th scope="col" className="px-3 py-2">Heartbeat</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Pool</th>
                  <th scope="col" className="hidden px-3 py-2 sm:table-cell">Active</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Queues</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Last seen</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.workers.map((worker) => (
                  <tr
                    key={worker.worker_id}
                    className="border-b border-border last:border-0 hover:bg-hover"
                  >
                    <td className="px-3 py-2">
                      <p className="break-all font-mono text-xs text-text-primary">
                        {worker.worker_id}
                      </p>
                      <div className="mt-1 md:hidden">
                        <span className="text-xs text-text-secondary">{worker.pool}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <WorkerChip worker={worker} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                      {worker.pool}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary sm:table-cell">
                      {formatCount(worker.active_tasks)}
                    </td>
                    <td className="hidden px-3 py-2 lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {worker.queues.map((name) => (
                          <QueueChip key={name} name={name} />
                        ))}
                      </div>
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {worker.last_seen_at ? formatAge(worker.last_seen_at) : "never"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

interface RowProps {
  queue: QueueHealth;
  workers: ReturnType<typeof workersForQueue>;
  activity: ReturnType<typeof queueActivity>;
}

function QueueRow({ queue, workers, activity }: RowProps): JSX.Element {
  return (
    <tr className={`border-b border-border last:border-0 ${isStalled(queue) ? "bg-[color-mix(in_srgb,var(--color-danger)_8%,transparent)]" : ""}`}>
      <td className="px-3 py-2">
        <div className="flex flex-wrap items-center gap-1">
          <QueueChip name={queue.name} />
          <PriorityChip priority={queue.priority} />
          {isStalled(queue) ? <StalledChip /> : null}
        </div>
        <p className="mt-1 max-w-md text-xs text-text-secondary">{queue.purpose}</p>
      </td>
      <td className="px-3 py-2">
        <DepthChip depth={queue.depth} workers={queue.workers} />
      </td>
      <td className="hidden px-3 py-2 md:table-cell">
        {workers.length === 0 ? (
          <span className="text-xs text-danger">none</span>
        ) : (
          <span className="text-text-secondary" title={workers.map((w) => w.worker_id).join(", ")}>
            {formatCount(workers.length)}
          </span>
        )}
      </td>
      <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
        {formatCount(activity.running)}
      </td>
      <td className="hidden px-3 py-2 lg:table-cell">
        {activity.failed > 0 ? (
          <Link
            to={`/operations/jobs?status=failure&queue=${encodeURIComponent(queue.name)}`}
            className="text-danger hover:underline"
          >
            {formatCount(activity.failed)}
          </Link>
        ) : (
          <span className="text-text-disabled">0</span>
        )}
      </td>
      <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
        {formatCount(activity.retryAttempts)}
        {activity.retrying > 0 ? (
          <span className="ml-1 text-xs text-warning">({activity.retrying} waiting)</span>
        ) : null}
      </td>
      <td className="hidden px-3 py-2 xl:table-cell">
        <span className="font-mono text-xs text-text-secondary">{queue.failure_destination}</span>
      </td>
    </tr>
  );
}
