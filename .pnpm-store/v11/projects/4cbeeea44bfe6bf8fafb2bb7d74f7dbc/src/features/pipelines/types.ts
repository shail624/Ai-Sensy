import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Pipeline = components["schemas"]["LeadPipelineResponse"];
export type Stage = components["schemas"]["LeadStageResponse"];
export type PipelineCreateRequest = components["schemas"]["LeadPipelineCreateRequest"];
export type PipelineUpdateRequest = components["schemas"]["LeadPipelineUpdateRequest"];
export type StageCreateRequest = components["schemas"]["LeadStageCreateRequest"];
export type StageUpdateRequest = components["schemas"]["LeadStageUpdateRequest"];

/** `String(80)` on both models, and the bound both create schemas declare. */
export const MAX_NAME_LENGTH = 80;

/**
 * A pipeline can be archived only when it is not the default — the server answers 409 otherwise,
 * because an organization must always have one pipeline to fall back on.
 */
export function isDeletable(pipeline: Pipeline): boolean {
  return !pipeline.is_default;
}

/**
 * Whether the default can be moved to this pipeline.
 *
 * Setting `is_default` clears it from whichever pipeline held it, so the flag moves rather than
 * being granted. Note the asymmetry the service enforces: `update_pipeline` acts only on a **truthy**
 * `is_default`, so the flag can be moved but never cleared — there is no way to leave an
 * organization with no default.
 */
export function canBecomeDefault(pipeline: Pipeline): boolean {
  return !pipeline.is_default;
}

/** A stage that ends the journey — nothing follows it. */
export function isTerminal(stage: Stage): boolean {
  return stage.is_terminal;
}

/** Stages as the pipeline orders them; `position` is dense (0…n−1) after every server-side move. */
export function orderedStages(pipeline: Pipeline): Stage[] {
  return [...pipeline.stages].sort((a, b) => a.position - b.position);
}

export function canMoveUp(stages: Stage[], index: number): boolean {
  return index > 0 && stages.length > 1;
}

export function canMoveDown(stages: Stage[], index: number): boolean {
  return index < stages.length - 1 && stages.length > 1;
}

/**
 * Where a stage lands when dropped onto another row.
 *
 * The server re-indexes siblings densely around the moved stage, so the target is simply the
 * destination index — no gap arithmetic, and one PATCH is enough for a whole move.
 */
export function targetPosition(from: number, to: number): number {
  return Math.max(0, to === from ? from : to);
}

// --- List query (client-side; see `api.ts` for why) -----------------------------------------------

export type PipelineSort = "name" | "-name" | "-stages" | "-updated_at";

export interface PipelineListQuery {
  q: string;
  /** "" = any · "default" · "custom" */
  kind: string;
  sort: PipelineSort;
}

export const DEFAULT_LIST_QUERY: PipelineListQuery = { q: "", kind: "", sort: "name" };

export const SORT_LABELS: Record<PipelineSort, string> = {
  name: "Name (A–Z)",
  "-name": "Name (Z–A)",
  "-stages": "Most stages",
  "-updated_at": "Recently changed",
};
