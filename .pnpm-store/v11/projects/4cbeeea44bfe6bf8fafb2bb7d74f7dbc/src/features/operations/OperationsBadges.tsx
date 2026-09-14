import type { Worker } from "@/features/operations/types";
import {
  isWorkerStale,
  JOB_STATUS_LABELS,
  PRIORITY_DESCRIPTIONS,
  priorityLabel,
} from "@/features/operations/types";

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

const JOB_TONE: Record<string, string> = {
  queued: "border-border text-text-secondary",
  started: "border-accent text-accent",
  success: "border-success text-success",
  failure: "border-danger text-danger",
  retry: "border-warning text-warning",
  revoked: "border-border text-text-disabled",
};

export function JobStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(JOB_TONE[value] ?? "border-border text-text-primary")}>
      {JOB_STATUS_LABELS[value] ?? value}
    </span>
  );
}

/**
 * Queue priority, P0 highest.
 *
 * Shown on a job row as well as a queue row, because a job's urgency is entirely a function of the
 * queue it was routed to — the job itself carries no priority of its own.
 */
export function PriorityChip({ priority }: { priority: number }): JSX.Element {
  const tone =
    priority <= 1
      ? "border-accent text-accent"
      : priority >= 4
        ? "border-border text-text-disabled"
        : "border-border text-text-secondary";
  return (
    <span title={PRIORITY_DESCRIPTIONS[priority]} className={chip(tone)}>
      {priorityLabel(priority)}
    </span>
  );
}

export function QueueChip({ name }: { name: string }): JSX.Element {
  return <span className={chip("border-border font-mono text-text-secondary")}>{name}</span>;
}

/** Backlog depth, toned by whether anything is consuming it. */
export function DepthChip({ depth, workers }: { depth: number; workers: number }): JSX.Element {
  if (depth === 0) {
    return <span className={chip("border-border text-text-disabled")}>Empty</span>;
  }
  const stalled = workers === 0;
  return (
    <span className={chip(stalled ? "border-danger text-danger" : "border-info text-info")}>
      {depth.toLocaleString()} waiting
    </span>
  );
}

/** A queue holding work with no worker consuming it — the state worth alerting on. */
export function StalledChip(): JSX.Element {
  return <span className={chip("border-danger text-danger")}>No worker</span>;
}

/** Worker liveness, from the heartbeat registry rather than from anything the worker claims. */
export function WorkerChip({ worker }: { worker: Worker }): JSX.Element {
  const stale = isWorkerStale(worker);
  return (
    <span className={chip(stale ? "border-warning text-warning" : "border-success text-success")}>
      {stale ? "Stale heartbeat" : "Live"}
    </span>
  );
}

/** Attempt count, marked once a job has needed more than one. */
export function AttemptsChip({ attempts }: { attempts: number }): JSX.Element {
  if (attempts <= 1) {
    return <span className="text-text-secondary">{attempts}</span>;
  }
  return (
    <span className={chip("border-warning text-warning")}>
      {attempts} attempts
    </span>
  );
}
