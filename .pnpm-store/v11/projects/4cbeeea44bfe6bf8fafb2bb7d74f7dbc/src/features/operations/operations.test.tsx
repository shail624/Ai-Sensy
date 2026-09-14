import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { JobActions } from "@/features/operations/JobActions";
import { JobList } from "@/features/operations/JobList";
import {
  AttemptsChip,
  DepthChip,
  JobStatusChip,
  PriorityChip,
  WorkerChip,
} from "@/features/operations/OperationsBadges";
import { QueueMonitor } from "@/features/operations/QueueMonitor";
import {
  durationMs,
  fleetSummary,
  isStalled,
  jobQueues,
  jobSummary,
  matchesJob,
  PAGE_SIZE,
  queueActivity,
  queuedMs,
  selectJobPage,
  sortQueuesByAttention,
  workersForQueue,
} from "@/features/operations/selectors";
import type { Job, JobListQuery, QueueHealth, Worker } from "@/features/operations/types";
import {
  DEFAULT_JOB_QUERY,
  isCancellable,
  isTerminal,
  isWorkerStale,
  wasRetried,
} from "@/features/operations/types";

// --- Fixtures -----------------------------------------------------------------------------------

function jobFixture(overrides: Partial<Job> = {}): Job {
  return {
    id: "j1",
    type: "job",
    task_name: "app.crm.tasks.import_contacts",
    queue: "imports",
    status: "success",
    ref_type: "import",
    ref_id: 42,
    attempts: 1,
    error_detail: null,
    result: { rows: 120 },
    started_at: "2026-07-23T10:00:05Z",
    finished_at: "2026-07-23T10:00:35Z",
    created_at: "2026-07-23T10:00:00Z",
    ...overrides,
  };
}

function queueFixture(overrides: Partial<QueueHealth> = {}): QueueHealth {
  return {
    name: "imports",
    purpose: "Chunked contact import: parse, validate, dedup, upsert.",
    priority: 3,
    pool: "jobs",
    depth: 0,
    workers: 1,
    failure_destination: "job=failed",
    ...overrides,
  };
}

function workerFixture(overrides: Partial<Worker> = {}): Worker {
  return {
    worker_id: "worker-jobs-1",
    pool: "jobs",
    queues: ["imports", "exports"],
    active_tasks: 2,
    started_at: "2026-07-23T09:00:00Z",
    last_seen_at: new Date().toISOString(),
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = { value: ["system:read", "system:manage"] };

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET: get, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function query(overrides: Partial<JobListQuery> = {}): JobListQuery {
  return { ...DEFAULT_JOB_QUERY, ...overrides };
}

beforeEach(() => {
  permissions.value = ["system:read", "system:manage"];
  for (const key of Object.keys(responses)) delete responses[key];
});

// --- Job state -----------------------------------------------------------------------------------

describe("job state", () => {
  it("treats success, failure and revoked as terminal", () => {
    expect(isTerminal(jobFixture({ status: "success" }))).toBe(true);
    expect(isTerminal(jobFixture({ status: "failure" }))).toBe(true);
    expect(isTerminal(jobFixture({ status: "revoked" }))).toBe(true);
    expect(isTerminal(jobFixture({ status: "started" }))).toBe(false);
    expect(isTerminal(jobFixture({ status: "retry" }))).toBe(false);
  });

  it("offers cancel only while a job can still move", () => {
    // Mirrors the server's own guard: cancelling a terminal job answers 409.
    expect(isCancellable(jobFixture({ status: "queued" }))).toBe(true);
    expect(isCancellable(jobFixture({ status: "success" }))).toBe(false);
  });

  it("counts a job as retried once it has run more than once", () => {
    expect(wasRetried(jobFixture({ attempts: 1 }))).toBe(false);
    expect(wasRetried(jobFixture({ attempts: 3 }))).toBe(true);
  });
});

describe("durations", () => {
  it("measures running time and queue wait separately", () => {
    const job = jobFixture();
    expect(durationMs(job)).toBe(30_000);
    expect(queuedMs(job)).toBe(5_000);
  });

  it("has no duration for a job that has not finished", () => {
    expect(durationMs(jobFixture({ finished_at: null }))).toBeNull();
    expect(queuedMs(jobFixture({ started_at: null }))).toBeNull();
  });
});

// --- Job selectors --------------------------------------------------------------------------------

describe("selectors — jobs", () => {
  const rows = [
    jobFixture({ id: "a", task_name: "app.crm.tasks.import_contacts", queue: "imports", status: "success", attempts: 1, created_at: "2026-07-23T10:00:00Z" }),
    jobFixture({ id: "b", task_name: "app.channels.tasks.send_message", queue: "sends.bulk", status: "failure", attempts: 5, error_detail: "ConnectionError: timed out", created_at: "2026-07-23T11:00:00Z" }),
    jobFixture({ id: "c", task_name: "app.analytics.tasks.rollup_nightly", queue: "analytics.rollup", status: "started", attempts: 1, finished_at: null, created_at: "2026-07-23T12:00:00Z" }),
  ];

  it("searches the task name, the queue and the failure text", () => {
    expect(matchesJob(rows[1]!, "timed out")).toBe(true);
    expect(matchesJob(rows[1]!, "sends.bulk")).toBe(true);
    expect(matchesJob(rows[0]!, "import_contacts")).toBe(true);
    expect(matchesJob(rows[0]!, "nothing")).toBe(false);
  });

  it("filters by status and queue", () => {
    expect(selectJobPage(rows, query({ status: "failure" })).rows.map((r) => r.id)).toEqual(["b"]);
    expect(selectJobPage(rows, query({ queue: "imports" })).rows.map((r) => r.id)).toEqual(["a"]);
  });

  it("sorts unfinished jobs last when ordering by duration", () => {
    // A job with no duration yet is not "instant" — it must not lead the longest-running list.
    const sorted = selectJobPage(rows, query({ sort: "duration" })).rows;
    expect(sorted[sorted.length - 1]?.id).toBe("c");
  });

  it("sorts by attempts and recency", () => {
    expect(selectJobPage(rows, query({ sort: "-attempts" })).rows[0]?.id).toBe("b");
    expect(selectJobPage(rows, query({ sort: "-created_at" })).rows[0]?.id).toBe("c");
  });

  it("clamps a page past the end and slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 4 }, (_, index) =>
      jobFixture({ id: `j${index}` }),
    );
    expect(selectJobPage(many, query()).rows).toHaveLength(PAGE_SIZE);
    expect(selectJobPage(many, query({ page: 2 })).rows).toHaveLength(4);
    expect(selectJobPage(many, query({ page: 99 })).page).toBe(2);
  });

  it("offers only the queues present among the loaded jobs", () => {
    expect(jobQueues(rows)).toEqual(["analytics.rollup", "imports", "sends.bulk"]);
    expect(jobQueues([jobFixture({ queue: null })])).toEqual([]);
  });

  it("summarises the loaded jobs by state", () => {
    expect(jobSummary(rows)).toEqual({
      total: 3,
      running: 1,
      queued: 0,
      failed: 1,
      retrying: 0,
      retried: 1,
    });
  });
});

// --- Queue selectors -------------------------------------------------------------------------------

describe("selectors — queues", () => {
  it("flags a queue holding work that nothing consumes", () => {
    expect(isStalled(queueFixture({ depth: 12, workers: 0 }))).toBe(true);
    expect(isStalled(queueFixture({ depth: 0, workers: 0 }))).toBe(false);
    expect(isStalled(queueFixture({ depth: 12, workers: 2 }))).toBe(false);
  });

  it("sorts a stalled queue above a deeper healthy one", () => {
    // Backlog with no worker is the failure mode that silently stops the platform.
    const ordered = sortQueuesByAttention([
      queueFixture({ name: "deep", depth: 900, workers: 3 }),
      queueFixture({ name: "stalled", depth: 1, workers: 0 }),
    ]);
    expect(ordered.map((queue) => queue.name)).toEqual(["stalled", "deep"]);
  });

  it("resolves worker assignment from the heartbeat registry", () => {
    const workers = [workerFixture(), workerFixture({ worker_id: "w2", queues: ["sends.bulk"] })];
    expect(workersForQueue(workers, "imports").map((w) => w.worker_id)).toEqual(["worker-jobs-1"]);
    expect(workersForQueue(workers, "ai")).toEqual([]);
  });

  it("derives per-queue activity from the loaded jobs", () => {
    const jobs = [
      jobFixture({ queue: "imports", status: "started", attempts: 1 }),
      jobFixture({ queue: "imports", status: "failure", attempts: 4 }),
      jobFixture({ queue: "imports", status: "retry", attempts: 2 }),
      jobFixture({ queue: "exports", status: "failure", attempts: 9 }),
    ];
    expect(queueActivity(jobs, "imports")).toEqual({
      running: 1,
      failed: 1,
      retrying: 1,
      // Attempts beyond the first are the retries: 0 + 3 + 1.
      retryAttempts: 4,
    });
  });

  it("summarises the fleet, counting stale heartbeats", () => {
    const now = Date.parse("2026-07-23T12:00:00Z");
    const summary = fleetSummary(
      [queueFixture({ depth: 5, workers: 1 }), queueFixture({ name: "ai", depth: 2, workers: 0 })],
      [
        workerFixture({ last_seen_at: "2026-07-23T11:59:50Z", active_tasks: 2 }),
        workerFixture({ worker_id: "w2", last_seen_at: "2026-07-23T11:00:00Z", active_tasks: 0 }),
      ],
      now,
    );
    expect(summary).toEqual({
      queues: 2,
      depth: 7,
      workers: 2,
      staleWorkers: 1,
      activeTasks: 2,
      stalledQueues: 1,
    });
  });

  it("treats a worker that has never reported as stale", () => {
    expect(isWorkerStale(workerFixture({ last_seen_at: null }))).toBe(true);
  });
});

// --- Badges ---------------------------------------------------------------------------------------

describe("OperationsBadges", () => {
  it("labels job statuses and passes unknown ones through verbatim", () => {
    withProviders(
      <>
        <JobStatusChip value="started" />
        <JobStatusChip value="some_new_state" />
      </>,
    );
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("some_new_state")).toBeInTheDocument();
  });

  it("calls an empty queue empty rather than showing a zero", () => {
    withProviders(<DepthChip depth={0} workers={1} />);
    expect(screen.getByText("Empty")).toBeInTheDocument();
  });

  it("shows backlog depth", () => {
    withProviders(<DepthChip depth={42} workers={0} />);
    expect(screen.getByText("42 waiting")).toBeInTheDocument();
  });

  it("only marks attempts once there has been more than one", () => {
    const single = withProviders(<AttemptsChip attempts={1} />);
    expect(single.container.textContent).toBe("1");
    withProviders(<AttemptsChip attempts={4} />);
    expect(screen.getByText("4 attempts")).toBeInTheDocument();
  });

  it("renders queue priority", () => {
    withProviders(<PriorityChip priority={0} />);
    expect(screen.getByText("P0")).toBeInTheDocument();
  });

  it("reports a stale heartbeat", () => {
    withProviders(<WorkerChip worker={workerFixture({ last_seen_at: "2020-01-01T00:00:00Z" })} />);
    expect(screen.getByText("Stale heartbeat")).toBeInTheDocument();
  });
});

// --- Actions ----------------------------------------------------------------------------------------

describe("JobActions", () => {
  it("offers cancel for a job that has not finished", () => {
    withProviders(<JobActions job={jobFixture({ status: "queued" })} />);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("offers nothing for a finished job", () => {
    withProviders(<JobActions job={jobFixture({ status: "success" })} />);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    expect(screen.getByText("Finished")).toBeInTheDocument();
  });

  it("never offers a retry, because no endpoint exists for one", () => {
    withProviders(<JobActions job={jobFixture({ status: "failure" })} />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("hides cancel from a read-only operator", () => {
    permissions.value = ["system:read"];
    withProviders(<JobActions job={jobFixture({ status: "queued" })} />);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("explains that cancelling a running job does not terminate it", () => {
    withProviders(<JobActions job={jobFixture({ status: "started" })} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      within(screen.getByRole("dialog")).getByText(/without terminating the worker/),
    ).toBeInTheDocument();
  });
});

// --- Lists (real hooks, stubbed transport) --------------------------------------------------------

describe("JobList", () => {
  function seed(jobs: Job[], total = jobs.length) {
    responses["/api/v1/jobs"] = { data: jobs, page: { limit: 50, has_more: false, total } };
    responses["/api/v1/queues"] = {
      queues: [queueFixture()],
      workers: [workerFixture()],
      dead_letter_parked: 0,
    };
  }

  it("lists jobs with status, attempts and duration", async () => {
    seed([jobFixture({ attempts: 3 })]);
    withProviders(<JobList />);

    expect(await screen.findByRole("link", { name: /import_contacts/ })).toHaveAttribute(
      "href",
      "/operations/jobs/j1",
    );
    // Scoped to the row: "Succeeded" is also a status-filter option.
    const row = screen
      .getAllByRole("row")
      .find((entry) => within(entry).queryByRole("link", { name: /import_contacts/ }))!;
    expect(within(row).getByText("Succeeded")).toBeInTheDocument();
    expect(within(row).getByText("3 attempts")).toBeInTheDocument();
    expect(within(row).getByText("30.0s")).toBeInTheDocument();
  });

  it("shows the queue's priority on a job row, since a job carries none of its own", async () => {
    seed([jobFixture()]);
    withProviders(<JobList />);
    await screen.findByRole("link", { name: /import_contacts/ });
    expect(screen.getByText("P3")).toBeInTheDocument();
  });

  it("surfaces the failure reason in the row", async () => {
    seed([jobFixture({ status: "failure", error_detail: "ConnectionError: timed out" })]);
    withProviders(<JobList />);
    expect(await screen.findByText("ConnectionError: timed out")).toBeInTheDocument();
  });

  it("filters by status without a round trip", async () => {
    seed([
      jobFixture({ id: "a", task_name: "task.alpha", status: "success" }),
      jobFixture({ id: "b", task_name: "task.bravo", status: "failure" }),
    ]);
    withProviders(<JobList />);

    await screen.findByRole("link", { name: "task.alpha" });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "failure" } });

    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "task.alpha" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "task.bravo" })).toBeInTheDocument();
  });

  it("says when more jobs exist than were loaded", async () => {
    seed([jobFixture()], 900);
    withProviders(<JobList />);
    expect(await screen.findByText(/900 jobs exist/)).toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<JobList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("QueueMonitor", () => {
  function seed(
    queues: QueueHealth[],
    workers: Worker[],
    parked = 0,
    jobs: Job[] = [],
  ) {
    responses["/api/v1/queues"] = { queues, workers, dead_letter_parked: parked };
    responses["/api/v1/jobs"] = { data: jobs, page: { limit: 50, has_more: false, total: jobs.length } };
  }

  it("lists queues with depth, purpose and worker coverage", async () => {
    seed([queueFixture({ depth: 7 })], [workerFixture()]);
    withProviders(<QueueMonitor />);

    // Scoped to the queue row: a queue name also appears on every worker that consumes it.
    expect(await screen.findByText("7 waiting")).toBeInTheDocument();
    const row = screen.getAllByRole("row").find((entry) => within(entry).queryByText("7 waiting"))!;
    expect(within(row).getByText("imports")).toBeInTheDocument();
    expect(within(row).getByText(/Chunked contact import/)).toBeInTheDocument();
  });

  it("raises an alarm when a queue holds work nothing is consuming", async () => {
    seed([queueFixture({ depth: 4, workers: 0 })], [workerFixture({ queues: ["other"] })]);
    withProviders(<QueueMonitor />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /queue holds work that no live worker is consuming/,
    );
    expect(screen.getByText("No worker")).toBeInTheDocument();
  });

  it("raises a louder alarm when no worker has reported at all", async () => {
    seed([queueFixture()], []);
    withProviders(<QueueMonitor />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/No worker has reported a heartbeat/);
  });

  it("says dead-letter entries cannot be acted on from here", async () => {
    seed([queueFixture()], [workerFixture()], 3);
    withProviders(<QueueMonitor />);
    expect(await screen.findByText(/no endpoint to inspect or replay them/)).toBeInTheDocument();
  });

  it("labels the derived counts as a sample of recent jobs, not queue totals", async () => {
    seed([queueFixture()], [workerFixture()], 0, [jobFixture({ status: "failure" })]);
    withProviders(<QueueMonitor />);
    expect(
      await screen.findByText(/a sample of recent activity, not queue totals/),
    ).toBeInTheDocument();
  });

  it("lists live workers with their pools and queues", async () => {
    seed([queueFixture()], [workerFixture()]);
    withProviders(<QueueMonitor />);
    expect(await screen.findByText("worker-jobs-1")).toBeInTheDocument();
    expect(screen.getAllByText("Live").length).toBeGreaterThan(0);
  });
});

// --- Navigation ---------------------------------------------------------------------------------------

describe("navigation — operations entry", () => {
  it("is visible to someone holding system:read", () => {
    expect(visibleNavItems((code) => code === "system:read").map((item) => item.path)).toContain(
      "/operations",
    );
  });

  it("is hidden from someone without it", () => {
    expect(visibleNavItems((code) => code === "inbox:read").map((item) => item.path)).not.toContain(
      "/operations",
    );
  });
});
