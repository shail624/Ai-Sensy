import type { Pipeline, PipelineListQuery, PipelineSort } from "@/features/pipelines/types";
import { MAX_NAME_LENGTH, orderedStages } from "@/features/pipelines/types";

const COMPARATORS: Record<PipelineSort, (a: Pipeline, b: Pipeline) => number> = {
  name: (a, b) => a.name.localeCompare(b.name),
  "-name": (a, b) => b.name.localeCompare(a.name),
  "-stages": (a, b) => b.stages.length - a.stages.length,
  "-updated_at": (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
};

/** Matches the pipeline name or any of its stage names — a stage is how people find a pipeline. */
export function matchesSearch(pipeline: Pipeline, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    pipeline.name.toLowerCase().includes(needle) ||
    pipeline.stages.some((stage) => stage.name.toLowerCase().includes(needle))
  );
}

export function filterPipelines(pipelines: Pipeline[], query: PipelineListQuery): Pipeline[] {
  return pipelines.filter(
    (pipeline) =>
      matchesSearch(pipeline, query.q) &&
      (query.kind === "" ||
        (query.kind === "default" ? pipeline.is_default : !pipeline.is_default)),
  );
}

/**
 * The default pipeline sorts first regardless of the chosen order.
 *
 * It is the one every new lead falls into, so burying it under an alphabetical neighbour would hide
 * the most consequential row on the screen.
 */
export function selectPipelines(pipelines: Pipeline[], query: PipelineListQuery): Pipeline[] {
  return [...filterPipelines(pipelines, query)].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return COMPARATORS[query.sort](a, b);
  });
}

export interface PipelineSummary {
  total: number;
  stages: number;
  /** Pipelines with no stages — configured but unusable, so worth counting separately. */
  empty: number;
  hasDefault: boolean;
}

export function pipelineSummary(pipelines: Pipeline[]): PipelineSummary {
  return {
    total: pipelines.length,
    stages: pipelines.reduce((sum, pipeline) => sum + pipeline.stages.length, 0),
    empty: pipelines.filter((pipeline) => pipeline.stages.length === 0).length,
    hasDefault: pipelines.some((pipeline) => pipeline.is_default),
  };
}

/** Terminal stages of a pipeline — the outcomes a lead can end on. */
export function terminalStages(pipeline: Pipeline): string[] {
  return orderedStages(pipeline)
    .filter((stage) => stage.is_terminal)
    .map((stage) => stage.name);
}

// --- Validation ------------------------------------------------------------------------------------

/**
 * Whether a name may be used, mirroring the server's uniqueness checks.
 *
 * Pipelines are unique per organization and stages per pipeline; both answer 409. Catching it here
 * turns a rejected save into immediate feedback, and the comparison is case-insensitive because a
 * near-duplicate is a mistake even where the database would allow it.
 */
export function validateName(
  name: string,
  existing: string[],
  { currentName }: { currentName?: string } = {},
): string | null {
  const trimmed = name.trim();
  if (trimmed === "") return "Name is required";
  if (trimmed.length > MAX_NAME_LENGTH) {
    return `Name is limited to ${MAX_NAME_LENGTH} characters`;
  }
  const taken = existing
    .filter((entry) => entry.toLowerCase() !== (currentName ?? "").toLowerCase())
    .some((entry) => entry.toLowerCase() === trimmed.toLowerCase());
  return taken ? "That name is already used" : null;
}

/**
 * The stage list after a move, used to preview the outcome before the request lands.
 *
 * Mirrors `_place_stage`: the stage is lifted out, re-inserted at the clamped target, and the whole
 * list re-indexed densely — so the preview and the server agree on where everything ends up.
 */
export function reorder<T>(items: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || from >= items.length) return items;
  const next = [...items];
  const [moved] = next.splice(from, 1);
  if (moved === undefined) return items;
  next.splice(Math.max(0, Math.min(to, next.length)), 0, moved);
  return next;
}
