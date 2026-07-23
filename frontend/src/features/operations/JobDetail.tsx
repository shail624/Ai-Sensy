import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useJob, useQueues } from "@/features/operations/api";
import { JobActions } from "@/features/operations/JobActions";
import {
  AttemptsChip,
  JobStatusChip,
  PriorityChip,
  QueueChip,
} from "@/features/operations/OperationsBadges";
import { durationMs, queuedMs, workersForQueue } from "@/features/operations/selectors";
import type { Job } from "@/features/operations/types";
import { JOB_STATUS_EXPLANATIONS } from "@/features/operations/types";
// Elapsed time, not playback time — see the note in `JobList`.
import { formatDuration } from "@/features/analytics/format";
import { formatDateTime, UNKNOWN } from "@/lib/format";

/**
 * One background job in full (Doc 05 B11.8) — what it was, how it went, how long it took, and what
 * it left behind.
 *
 * Polled only while it can still move: a terminal job's record never changes again.
 */
export function JobDetail({ jobId }: { jobId: string }): JSX.Element {
  const navigate = useNavigate();
  const job = useJob(jobId);
  const data = job.data;

  if (job.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading job…" />
      </PageContainer>
    );
  }

  if (job.isError || !data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Jobs", to: "/operations/jobs" }, { label: "Job" }]} />
        <ErrorState message={apiErrorMessage(job.error)} onRetry={() => void job.refetch()} />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Jobs", to: "/operations/jobs" }, { label: data.task_name }]} />
      <PageHeader
        title={data.task_name}
        description={data.queue ? `Queued on ${data.queue}` : "No queue recorded"}
        actions={<JobActions job={data} onCancelled={() => navigate("/operations/jobs")} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <JobStatusChip value={data.status} />
        <AttemptsChip attempts={data.attempts} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ExecutionSection job={data} />
        <MetadataSection job={data} />
      </div>

      <div className="mt-4 space-y-4">
        {data.error_detail ? <FailureSection job={data} /> : null}
        <ResultSection job={data} />
      </div>
    </PageContainer>
  );
}

/**
 * How the job ran: when it was accepted, when a worker took it, how long it waited, how long it
 * took, and how many attempts it needed.
 *
 * There is no per-attempt history to show. `job_metadata` records an attempt **counter** plus one
 * `started_at`/`finished_at` pair — each retry overwrites the previous timings rather than
 * appending — so the honest rendering is a count and the latest run, not a timeline of attempts
 * the platform never stored.
 */
function ExecutionSection({ job }: { job: Job }): JSX.Element {
  const ran = durationMs(job);
  const waited = queuedMs(job);

  return (
    <Section title="Execution">
      <p className="mb-3 text-sm text-text-secondary">
        {JOB_STATUS_EXPLANATIONS[job.status] ?? "This job's status came from the worker framework."}
      </p>

      <ol className="mb-3 space-y-2">
        <Step label="Accepted" detail={formatDateTime(job.created_at)} done />
        <Step
          label="Picked up by a worker"
          detail={
            job.started_at
              ? `${formatDateTime(job.started_at)}${waited !== null ? ` · waited ${formatDuration(waited / 1000)}` : ""}`
              : "Not yet"
          }
          done={Boolean(job.started_at)}
        />
        <Step
          label="Finished"
          detail={
            job.finished_at
              ? `${formatDateTime(job.finished_at)}${ran !== null ? ` · ran for ${formatDuration(ran / 1000)}` : ""}`
              : "Still running or waiting"
          }
          done={Boolean(job.finished_at)}
        />
      </ol>

      <dl>
        <DefinitionRow label="Attempts">
          <AttemptsChip attempts={job.attempts} />
        </DefinitionRow>
        <DefinitionRow label="Time queued">
          {waited === null ? UNKNOWN : formatDuration(waited / 1000)}
        </DefinitionRow>
        <DefinitionRow label="Time running">
          {ran === null ? UNKNOWN : formatDuration(ran / 1000)}
        </DefinitionRow>
      </dl>

      {job.attempts > 1 ? (
        <p className="mt-3 text-xs text-text-disabled">
          This job was attempted {job.attempts} times. The timings above are the most recent
          attempt — the platform records an attempt count rather than a per-attempt history.
        </p>
      ) : null}
    </Section>
  );
}

function Step({
  label,
  detail,
  done,
}: {
  label: string;
  detail: string;
  done: boolean;
}): JSX.Element {
  return (
    <li className="flex gap-3">
      <span
        aria-hidden
        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${done ? "bg-success" : "bg-border"}`}
      />
      <div className="min-w-0">
        <p className={`text-sm ${done ? "text-text-primary" : "text-text-disabled"}`}>{label}</p>
        <p className="text-xs text-text-secondary">{detail}</p>
      </div>
    </li>
  );
}

/** What the job is and where it sits in the fleet, including the workers that could run it. */
function MetadataSection({ job }: { job: Job }): JSX.Element {
  const queues = useQueues(false);

  const spec = useMemo(
    () => (queues.data?.queues ?? []).find((queue) => queue.name === job.queue),
    [queues.data, job.queue],
  );
  const consumers = useMemo(
    () => (job.queue ? workersForQueue(queues.data?.workers ?? [], job.queue) : []),
    [queues.data, job.queue],
  );

  return (
    <Section title="Metadata">
      <dl>
        <DefinitionRow label="Task">
          <span className="break-all font-mono text-xs">{job.task_name}</span>
        </DefinitionRow>
        <DefinitionRow label="Queue">
          {job.queue ? (
            <div className="flex flex-wrap items-center gap-1">
              <QueueChip name={job.queue} />
              {spec ? <PriorityChip priority={spec.priority} /> : null}
            </div>
          ) : (
            UNKNOWN
          )}
        </DefinitionRow>
        <DefinitionRow label="Worker pool">{spec?.pool ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="On failure">{spec?.failure_destination ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="Related record">
          {job.ref_type ? `${job.ref_type}${job.ref_id !== null ? ` #${job.ref_id}` : ""}` : UNKNOWN}
        </DefinitionRow>
        <DefinitionRow label="Job id">
          <span className="break-all font-mono text-xs">{job.id}</span>
        </DefinitionRow>
      </dl>

      <div className="mt-3">
        <p className="text-xs font-medium text-text-secondary">Workers on this queue</p>
        {consumers.length === 0 ? (
          <p className="mt-1 text-xs text-text-disabled">
            {job.queue
              ? "No live worker is consuming this queue right now."
              : "No queue recorded for this job."}
          </p>
        ) : (
          <ul className="mt-1 flex flex-wrap gap-1">
            {consumers.map((worker) => (
              <li
                key={worker.worker_id}
                className="rounded-full border border-border px-2 py-0.5 font-mono text-xs text-text-secondary"
              >
                {worker.worker_id}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-text-disabled">
          These are the workers eligible to run this queue&apos;s work. The platform does not record
          which worker ran a specific job.
        </p>
      </div>
    </Section>
  );
}

/** Why it failed, verbatim. */
function FailureSection({ job }: { job: Job }): JSX.Element {
  const queues = useQueues(false);
  const spec = (queues.data?.queues ?? []).find((queue) => queue.name === job.queue);

  return (
    <Section title="Failure">
      <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-md border border-danger bg-surface-2 p-3 text-xs text-danger">
        {job.error_detail}
      </pre>
      {spec ? (
        <p className="mt-2 text-xs text-text-disabled">
          Work that exhausts its attempts on <span className="font-mono">{spec.name}</span> goes to{" "}
          <span className="font-mono">{spec.failure_destination}</span>.
        </p>
      ) : null}
      <p className="mt-2 text-xs text-text-disabled">
        There is no retry action here: the platform exposes no endpoint to re-run a finished job.
        Re-trigger the work from the surface that started it — a campaign retry, a fresh export, a
        template sync.
      </p>
    </Section>
  );
}

/**
 * What the job returned.
 *
 * The **input payload is not shown, because the API does not return it**: `job_metadata` stores
 * `args_json`, but `JobResponse` has no field for it. What is available is the result the task
 * produced and the record it refers to — enough to tell what a job touched, short of its arguments.
 */
function ResultSection({ job }: { job: Job }): JSX.Element {
  const empty = !job.result || Object.keys(job.result).length === 0;

  return (
    <Section title="Result">
      {empty ? (
        <EmptyState
          title="No result recorded"
          description={
            job.status === "success"
              ? "The task finished without returning anything."
              : "A result is written when the task completes."
          }
        />
      ) : (
        <pre className="overflow-x-auto rounded-md border border-border bg-surface-2 p-3 text-xs text-text-primary">
          {JSON.stringify(job.result, null, 2)}
        </pre>
      )}

      {job.ref_type ? (
        <p className="mt-2 text-xs text-text-secondary">
          Refers to {job.ref_type}
          {job.ref_id !== null ? ` #${job.ref_id}` : ""}.
        </p>
      ) : null}

      <p className="mt-2 text-xs text-text-disabled">
        The arguments this job was queued with are stored but not exposed by the API, so they are
        not shown here.{" "}
        <Link to="/admin/audit" className="text-accent hover:underline">
          The audit log
        </Link>{" "}
        records the action that started it.
      </p>
    </Section>
  );
}
