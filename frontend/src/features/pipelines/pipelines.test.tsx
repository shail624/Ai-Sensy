import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { PipelineActions } from "@/features/pipelines/PipelineActions";
import { DefaultChip, PositionChip, StageCountChip } from "@/features/pipelines/PipelineBadges";
import { PipelineDetail } from "@/features/pipelines/PipelineDetail";
import { PipelineFormDialog } from "@/features/pipelines/PipelineFormDialog";
import { PipelineList } from "@/features/pipelines/PipelineList";
import {
  filterPipelines,
  matchesSearch,
  pipelineSummary,
  reorder,
  selectPipelines,
  terminalStages,
  validateName,
} from "@/features/pipelines/selectors";
import { StageManager } from "@/features/pipelines/StageManager";
import type { Pipeline, PipelineListQuery, Stage } from "@/features/pipelines/types";
import {
  canBecomeDefault,
  canMoveDown,
  canMoveUp,
  DEFAULT_LIST_QUERY,
  isDeletable,
  orderedStages,
  targetPosition,
} from "@/features/pipelines/types";

// --- Fixtures -----------------------------------------------------------------------------------

function stageFixture(overrides: Partial<Stage> = {}): Stage {
  return {
    id: "st1",
    type: "lead_stage",
    name: "New Lead",
    position: 0,
    is_terminal: false,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

function pipelineFixture(overrides: Partial<Pipeline> = {}): Pipeline {
  return {
    id: "p1",
    type: "lead_pipeline",
    name: "Default",
    is_default: true,
    stages: [
      stageFixture({ id: "st1", name: "New Lead", position: 0 }),
      stageFixture({ id: "st2", name: "Interested", position: 1 }),
      stageFixture({ id: "st3", name: "Completed", position: 2, is_terminal: true }),
    ],
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = { value: ["contacts:read", "contacts:write"] };

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

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigate };
});

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};
const writes: { path: string; body: unknown; params: unknown }[] = [];

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async (path: string, init?: { body?: unknown; params?: unknown }) => {
    writes.push({ path, body: init?.body, params: init?.params });
    return path in responses
      ? { data: responses[path] }
      : { error: { detail: "network disabled under test" } };
  };
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

function query(overrides: Partial<PipelineListQuery> = {}): PipelineListQuery {
  return { ...DEFAULT_LIST_QUERY, ...overrides };
}

beforeEach(() => {
  permissions.value = ["contacts:read", "contacts:write"];
  for (const key of Object.keys(responses)) delete responses[key];
  writes.length = 0;
  navigate.mockClear();
});

// --- Business rules -------------------------------------------------------------------------------

describe("business rules", () => {
  it("refuses to archive the default pipeline, mirroring the server's 409", () => {
    expect(isDeletable(pipelineFixture({ is_default: true }))).toBe(false);
    expect(isDeletable(pipelineFixture({ is_default: false }))).toBe(true);
  });

  it("offers the default only to a pipeline that does not already hold it", () => {
    // The flag moves rather than being granted, and the server ignores a falsy value — so there is
    // no "remove default" to offer.
    expect(canBecomeDefault(pipelineFixture({ is_default: true }))).toBe(false);
    expect(canBecomeDefault(pipelineFixture({ is_default: false }))).toBe(true);
  });

  it("orders stages by position, not by array order", () => {
    const scrambled = pipelineFixture({
      stages: [
        stageFixture({ id: "b", name: "Second", position: 1 }),
        stageFixture({ id: "a", name: "First", position: 0 }),
      ],
    });
    expect(orderedStages(scrambled).map((s) => s.name)).toEqual(["First", "Second"]);
  });

  it("knows which stages can move", () => {
    const stages = orderedStages(pipelineFixture());
    expect(canMoveUp(stages, 0)).toBe(false);
    expect(canMoveUp(stages, 1)).toBe(true);
    expect(canMoveDown(stages, 2)).toBe(false);
    expect(canMoveDown(stages, 1)).toBe(true);
    // A lone stage cannot move anywhere.
    expect(canMoveUp([stageFixture()], 0)).toBe(false);
    expect(canMoveDown([stageFixture()], 0)).toBe(false);
  });

  it("resolves a drop target to the destination index", () => {
    expect(targetPosition(0, 2)).toBe(2);
    expect(targetPosition(2, 2)).toBe(2);
    expect(targetPosition(1, -5)).toBe(0);
  });

  it("lists a pipeline's final stages", () => {
    expect(terminalStages(pipelineFixture())).toEqual(["Completed"]);
    expect(terminalStages(pipelineFixture({ stages: [] }))).toEqual([]);
  });
});

// --- Reordering preview ------------------------------------------------------------------------------

describe("reorder", () => {
  it("moves an item and keeps the rest in order", () => {
    expect(reorder(["a", "b", "c"], 0, 2)).toEqual(["b", "c", "a"]);
    expect(reorder(["a", "b", "c"], 2, 0)).toEqual(["c", "a", "b"]);
  });

  it("is a no-op for a move that changes nothing or is out of range", () => {
    expect(reorder(["a", "b"], 1, 1)).toEqual(["a", "b"]);
    expect(reorder(["a", "b"], 5, 0)).toEqual(["a", "b"]);
    expect(reorder(["a", "b"], -1, 0)).toEqual(["a", "b"]);
  });

  it("clamps a target past the end", () => {
    expect(reorder(["a", "b", "c"], 0, 99)).toEqual(["b", "c", "a"]);
  });
});

// --- Validation --------------------------------------------------------------------------------------

describe("validateName", () => {
  it("requires a name and bounds it at the schema's limit", () => {
    expect(validateName("", [])).toMatch(/required/);
    expect(validateName("   ", [])).toMatch(/required/);
    expect(validateName("x".repeat(81), [])).toMatch(/80 characters/);
    expect(validateName("x".repeat(80), [])).toBeNull();
  });

  it("rejects a duplicate case-insensitively, ahead of the server's 409", () => {
    expect(validateName("Default", ["default"])).toMatch(/already used/);
    expect(validateName("Fresh", ["Default"])).toBeNull();
  });

  it("lets a rename keep its own name", () => {
    expect(validateName("Default", ["Default"], { currentName: "Default" })).toBeNull();
  });
});

// --- List selectors -------------------------------------------------------------------------------------

describe("selectors — list", () => {
  const rows = [
    pipelineFixture({ id: "a", name: "Alpha", is_default: false }),
    pipelineFixture({ id: "b", name: "Bravo", is_default: true }),
    pipelineFixture({ id: "c", name: "Charlie", is_default: false, stages: [] }),
  ];

  it("searches the pipeline name and its stage names", () => {
    expect(matchesSearch(rows[0]!, "alph")).toBe(true);
    // A stage name is how people remember a pipeline.
    expect(matchesSearch(rows[0]!, "Interested")).toBe(true);
    expect(matchesSearch(rows[0]!, "nothing")).toBe(false);
  });

  it("filters default from custom", () => {
    expect(filterPipelines(rows, query({ kind: "default" })).map((r) => r.id)).toEqual(["b"]);
    expect(filterPipelines(rows, query({ kind: "custom" })).map((r) => r.id)).toEqual(["a", "c"]);
  });

  it("always sorts the default first, whatever order is chosen", () => {
    // It is the pipeline every new lead falls into; burying it alphabetically would hide it.
    expect(selectPipelines(rows, query({ sort: "name" })).map((r) => r.id)).toEqual(["b", "a", "c"]);
    expect(selectPipelines(rows, query({ sort: "-name" })).map((r) => r.id)).toEqual(["b", "c", "a"]);
  });

  it("counts stages and pipelines with none", () => {
    expect(pipelineSummary(rows)).toEqual({ total: 3, stages: 6, empty: 1, hasDefault: true });
  });

  it("reports when no pipeline holds the default", () => {
    expect(pipelineSummary([pipelineFixture({ is_default: false })]).hasDefault).toBe(false);
  });
});

// --- Badges ----------------------------------------------------------------------------------------------

describe("PipelineBadges", () => {
  it("marks the default and warns about an empty pipeline", () => {
    withProviders(
      <>
        <DefaultChip />
        <StageCountChip count={0} />
      </>,
    );
    expect(screen.getByText("Default")).toBeInTheDocument();
    expect(screen.getByText("No stages")).toBeInTheDocument();
  });

  it("shows a stage's position one-based", () => {
    withProviders(<PositionChip position={0} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });
});

// --- StageManager -------------------------------------------------------------------------------------------

describe("StageManager — ordering", () => {
  it("moves a stage down with one PATCH carrying the destination index", async () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Move New Lead down" }));

    // One request expresses the whole move — the server re-indexes the siblings.
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/lead-stages/{stage_id}");
    expect(writes[0]?.body).toEqual({ position: 1 });
    expect(writes[0]?.params).toEqual({ path: { stage_id: "st1" } });
  });

  it("moves a stage up", async () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);
    fireEvent.click(screen.getByRole("button", { name: "Move Interested up" }));
    await waitFor(() => expect(writes[0]?.body).toEqual({ position: 0 }));
  });

  it("disables the moves that would go off either end", () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);
    expect(screen.getByRole("button", { name: "Move New Lead up" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move Completed down" })).toBeDisabled();
  });

  it("reorders by dropping one row onto another", async () => {
    const { container } = withProviders(<StageManager pipeline={pipelineFixture()} />);
    const rows = container.querySelectorAll("li[draggable='true']");

    fireEvent.dragStart(rows[0]!);
    fireEvent.dragOver(rows[2]!);
    fireEvent.drop(rows[2]!);

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({ position: 2 });
  });

  it("sends nothing when a stage is dropped on itself", async () => {
    const { container } = withProviders(<StageManager pipeline={pipelineFixture()} />);
    const rows = container.querySelectorAll("li[draggable='true']");

    fireEvent.dragStart(rows[1]!);
    fireEvent.drop(rows[1]!);

    await Promise.resolve();
    expect(writes).toHaveLength(0);
  });
});

describe("StageManager — CRUD", () => {
  it("adds a stage without a position, so it appends", async () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Add stage" }));
    fireEvent.change(screen.getByLabelText("Stage name"), { target: { value: "Verification" } });
    // Scoped to the dialog: the section header carries the same label.
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Add stage" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/lead-pipelines/{pipeline_id}/stages");
    // No position: a new stage appends, and is reordered afterwards if needed.
    expect(writes[0]?.body).toEqual({ name: "Verification", is_terminal: false });
  });

  it("refuses a duplicate stage name before sending it", () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Add stage" }));
    fireEvent.change(screen.getByLabelText("Stage name"), { target: { value: "interested" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Add stage" }));

    expect(screen.getByText("That name is already used")).toBeInTheDocument();
    expect(writes).toHaveLength(0);
  });

  it("edits a stage's name and final flag together", async () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);

    const row = screen.getByText("Interested").closest("li")!;
    fireEvent.click(within(row).getByRole("button", { name: "Edit" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Save stage" }));

    await waitFor(() =>
      expect(writes[0]?.body).toEqual({ name: "Interested", is_terminal: true }),
    );
  });

  it("confirms before archiving a stage and says it cannot be restored", () => {
    withProviders(<StageManager pipeline={pipelineFixture()} />);

    const row = screen.getByText("Interested").closest("li")!;
    fireEvent.click(within(row).getByRole("button", { name: "Archive" }));

    expect(
      within(screen.getByRole("dialog")).getByText(/no way to restore it/),
    ).toBeInTheDocument();
  });

  it("explains an empty pipeline rather than showing nothing", () => {
    withProviders(<StageManager pipeline={pipelineFixture({ stages: [] })} />);
    expect(screen.getByText("No stages")).toBeInTheDocument();
    expect(screen.getByText(/needs at least one stage/)).toBeInTheDocument();
  });

  it("hides every control from a reader, including dragging", () => {
    permissions.value = ["contacts:read"];
    const { container } = withProviders(<StageManager pipeline={pipelineFixture()} />);

    expect(screen.queryByRole("button", { name: "Add stage" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Move/ })).not.toBeInTheDocument();
    expect(container.querySelectorAll("li[draggable='true']")).toHaveLength(0);
  });
});

// --- PipelineFormDialog --------------------------------------------------------------------------------------

describe("PipelineFormDialog", () => {
  it("creates a pipeline with the default flag when asked", async () => {
    withProviders(<PipelineFormDialog existingNames={["Default"]} onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Pipeline name"), { target: { value: "Reactivation" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Create pipeline" }));

    await waitFor(() =>
      expect(writes[0]?.body).toEqual({ name: "Reactivation", is_default: true }),
    );
  });

  it("names the pipeline the default would move away from", () => {
    withProviders(
      <PipelineFormDialog existingNames={[]} currentDefault="Default" onClose={vi.fn()} />,
    );
    expect(screen.getByText(/moves the default away from/)).toBeInTheDocument();
  });

  it("omits the flag entirely when a rename does not move it", async () => {
    withProviders(
      <PipelineFormDialog
        pipeline={pipelineFixture({ is_default: false, name: "Old" })}
        existingNames={["Old"]}
        onClose={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Pipeline name"), { target: { value: "New name" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    // Sending `is_default: false` would be a no-op the server ignores, and noise in the audit entry.
    await waitFor(() => expect(writes[0]?.body).toEqual({ name: "New name" }));
  });

  it("explains that the default cannot simply be switched off", () => {
    withProviders(
      <PipelineFormDialog
        pipeline={pipelineFixture({ is_default: true })}
        existingNames={["Default"]}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/always has one/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("blocks a duplicate name before sending it", () => {
    withProviders(<PipelineFormDialog existingNames={["Taken"]} onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Pipeline name"), { target: { value: "taken" } });
    fireEvent.click(screen.getByRole("button", { name: "Create pipeline" }));

    expect(screen.getByText("That name is already used")).toBeInTheDocument();
    expect(writes).toHaveLength(0);
  });

  it("surfaces a server rejection verbatim", async () => {
    withProviders(<PipelineFormDialog existingNames={[]} onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Pipeline name"), { target: { value: "Anything" } });
    fireEvent.click(screen.getByRole("button", { name: "Create pipeline" }));

    expect(await screen.findByText("network disabled under test")).toBeInTheDocument();
  });
});

// --- PipelineActions -------------------------------------------------------------------------------------------

describe("PipelineActions", () => {
  it("offers neither archive nor make-default on the default pipeline", () => {
    withProviders(
      <PipelineActions pipeline={pipelineFixture({ is_default: true })} existingNames={[]} />,
    );
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Make default" })).not.toBeInTheDocument();
    expect(screen.getByText(/cannot be archived/)).toBeInTheDocument();
  });

  it("moves the default with a single PATCH", async () => {
    withProviders(
      <PipelineActions pipeline={pipelineFixture({ id: "p2", is_default: false })} existingNames={[]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Make default" }));
    await waitFor(() => expect(writes[0]?.body).toEqual({ is_default: true }));
  });

  it("warns that archiving takes the stages with it", () => {
    withProviders(
      <PipelineActions pipeline={pipelineFixture({ is_default: false })} existingNames={[]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Archive" }));
    expect(within(screen.getByRole("dialog")).getByText(/3 stages are archived together/)).toBeInTheDocument();
  });

  it("hides every write control from a reader", () => {
    permissions.value = ["contacts:read"];
    withProviders(
      <PipelineActions pipeline={pipelineFixture({ is_default: false })} existingNames={[]} />,
    );
    expect(screen.queryByRole("button", { name: "Rename" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
  });
});

// --- List ---------------------------------------------------------------------------------------------------------

describe("PipelineList", () => {
  it("lists pipelines with their stage order shown inline", async () => {
    responses["/api/v1/lead-pipelines"] = [pipelineFixture()];
    withProviders(<PipelineList />);

    expect(await screen.findByRole("link", { name: "Default" })).toHaveAttribute(
      "href",
      "/pipelines/p1",
    );
    expect(screen.getByText("New Lead")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getAllByText("3 stages").length).toBeGreaterThan(0);
  });

  it("warns when a pipeline has no final stage", async () => {
    responses["/api/v1/lead-pipelines"] = [
      pipelineFixture({ stages: [stageFixture({ is_terminal: false })] }),
    ];
    withProviders(<PipelineList />);
    expect(await screen.findByText(/nowhere to finish/)).toBeInTheDocument();
  });

  it("warns when no pipeline holds the default", async () => {
    responses["/api/v1/lead-pipelines"] = [pipelineFixture({ is_default: false })];
    withProviders(<PipelineList />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/nowhere to land/);
  });

  it("filters to custom pipelines without a round trip", async () => {
    responses["/api/v1/lead-pipelines"] = [
      pipelineFixture({ id: "a", name: "Default", is_default: true }),
      pipelineFixture({ id: "b", name: "Reactivation", is_default: false }),
    ];
    withProviders(<PipelineList />);

    await screen.findByRole("link", { name: "Default" });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "custom" } });

    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Default" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Reactivation" })).toBeInTheDocument();
  });

  it("invites a writer to create the first pipeline", async () => {
    responses["/api/v1/lead-pipelines"] = [];
    withProviders(<PipelineList />);
    expect(await screen.findByText("No pipelines")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New pipeline" })).toBeInTheDocument();
  });

  it("hides the create control from a reader", async () => {
    permissions.value = ["contacts:read"];
    responses["/api/v1/lead-pipelines"] = [];
    withProviders(<PipelineList />);
    await screen.findByText("No pipelines");
    expect(screen.queryByRole("button", { name: "New pipeline" })).not.toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<PipelineList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

// --- Detail --------------------------------------------------------------------------------------------------------

describe("PipelineDetail", () => {
  function seed(pipeline: Pipeline) {
    responses["/api/v1/lead-pipelines/{pipeline_id}"] = pipeline;
    responses["/api/v1/lead-pipelines"] = [pipeline];
  }

  it("shows the stages and the record", async () => {
    seed(pipelineFixture());
    withProviders(<PipelineDetail pipelineId="p1" />);

    expect(await screen.findByText("New Lead")).toBeInTheDocument();
    expect(screen.getByText("Yes — new leads land here")).toBeInTheDocument();
    // "Completed" is both a stage row and the record's final-stages entry.
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
  });

  it("warns when nothing is marked final", async () => {
    seed(pipelineFixture({ stages: [stageFixture({ is_terminal: false })] }));
    withProviders(<PipelineDetail pipelineId="p1" />);
    expect(await screen.findByText(/nowhere to finish/)).toBeInTheDocument();
  });

  it("says the platform records no lead counts against a stage", async () => {
    seed(pipelineFixture());
    withProviders(<PipelineDetail pipelineId="p1" />);
    expect(await screen.findByText(/no lead counts against a stage/)).toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<PipelineDetail pipelineId="p1" />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

// --- Navigation ------------------------------------------------------------------------------------------------------

describe("navigation — pipelines entry", () => {
  it("is visible to someone holding contacts:read, which leads reuse", () => {
    expect(visibleNavItems((code) => code === "contacts:read").map((item) => item.path)).toContain(
      "/pipelines",
    );
  });

  it("is hidden from someone without it", () => {
    expect(visibleNavItems((code) => code === "inbox:read").map((item) => item.path)).not.toContain(
      "/pipelines",
    );
  });
});
