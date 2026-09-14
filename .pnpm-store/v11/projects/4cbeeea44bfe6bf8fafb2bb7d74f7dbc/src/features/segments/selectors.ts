import type {
  AttributeDefinition,
  FieldSource,
  Segment,
  SegmentRule,
  ValueKind,
} from "@/features/segments/types";
import {
  fieldsForSource,
  isStale,
  MAX_DESCRIPTION_LENGTH,
  MAX_NAME_LENGTH,
  operatorsFor,
  shapeFor,
} from "@/features/segments/types";

/** Rows per page for the client-side list (see `useSegments` for why paging lives here). */
export const PAGE_SIZE = 25;

export type SegmentSort = "name" | "-name" | "-cached_count" | "-updated_at" | "-created_at";

export interface SegmentListQuery {
  q: string;
  /** "" = any · "evaluated" · "stale" · "empty" */
  state: string;
  match: string;
  sort: SegmentSort;
  page: number;
}

export const DEFAULT_LIST_QUERY: SegmentListQuery = {
  q: "",
  state: "",
  match: "",
  sort: "name",
  page: 1,
};

const COMPARATORS: Record<SegmentSort, (a: Segment, b: Segment) => number> = {
  name: (a, b) => a.name.localeCompare(b.name),
  "-name": (a, b) => b.name.localeCompare(a.name),
  // Never-evaluated segments sort last: no count is not "zero contacts".
  "-cached_count": (a, b) => (b.cached_count ?? -1) - (a.cached_count ?? -1),
  "-updated_at": (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
  "-created_at": (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
};

/** Matches the name or the description — the two things an operator writes when saving a filter. */
export function matchesSearch(segment: Segment, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    segment.name.toLowerCase().includes(needle) ||
    (segment.description ?? "").toLowerCase().includes(needle)
  );
}

function matchesState(segment: Segment, state: string): boolean {
  if (state === "") return true;
  if (state === "stale") return isStale(segment);
  if (state === "evaluated") return !isStale(segment);
  // "empty" means evaluated and found nobody — distinct from never evaluated.
  return !isStale(segment) && segment.cached_count === 0;
}

export function filterSegments(segments: Segment[], query: SegmentListQuery): Segment[] {
  return segments.filter(
    (segment) =>
      matchesSearch(segment, query.q) &&
      matchesState(segment, query.state) &&
      (query.match === "" || segment.match_type === query.match),
  );
}

export interface SegmentPage {
  rows: Segment[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, in that order, so the page numbers describe the filtered set. */
export function selectSegmentPage(
  segments: Segment[],
  query: SegmentListQuery,
): SegmentPage {
  const matched = [...filterSegments(segments, query)].sort(COMPARATORS[query.sort]);
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * PAGE_SIZE;
  return { rows: matched.slice(start, start + PAGE_SIZE), total: matched.length, totalPages, page };
}

export interface SegmentSummary {
  total: number;
  evaluated: number;
  stale: number;
  /** Contacts across every evaluated segment. Overlapping segments double-count, so it is a sum
   *  of segment sizes rather than a distinct-contact figure — and is labelled as such. */
  reach: number;
}

export function segmentSummary(segments: Segment[]): SegmentSummary {
  return {
    total: segments.length,
    evaluated: segments.filter((segment) => !isStale(segment)).length,
    stale: segments.filter(isStale).length,
    reach: segments.reduce((sum, segment) => sum + (segment.cached_count ?? 0), 0),
  };
}

// --- Rule grouping ----------------------------------------------------------------------------------

export interface RuleGroup {
  index: number;
  rules: SegmentRule[];
}

/**
 * Rules arranged into the groups the compiler evaluates.
 *
 * Rules sharing a `group_index` are ANDed together; the groups are then combined by the segment's
 * `match_type`. The wire format is a flat list, so grouping it is what makes the logic legible.
 */
export function groupRules(rules: SegmentRule[]): RuleGroup[] {
  const groups = new Map<number, SegmentRule[]>();
  for (const rule of rules) {
    const index = rule.group_index ?? 0;
    const existing = groups.get(index);
    if (existing) existing.push(rule);
    else groups.set(index, [rule]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a - b)
    .map(([index, groupRules]) => ({ index, rules: groupRules }));
}

/** Flatten groups back to the wire format, renumbering so gaps left by deletions do not persist. */
export function flattenGroups(groups: RuleGroup[]): SegmentRule[] {
  return groups
    .filter((group) => group.rules.length > 0)
    .flatMap((group, index) => group.rules.map((rule) => ({ ...rule, group_index: index })));
}

// --- Validation -------------------------------------------------------------------------------------

export interface SegmentProblems {
  name?: string;
  description?: string;
  /** Keyed `"<groupIndex>:<ruleIndex>"` so a message lands on the row that caused it. */
  rules: Record<string, string>;
}

function ruleValueProblem(rule: SegmentRule, kind: ValueKind): string | null {
  const shape = shapeFor(rule.operator);

  if (shape === "boolean") {
    return typeof rule.value === "boolean" ? null : "Choose yes or no";
  }
  if (shape === "range") {
    if (!Array.isArray(rule.value) || rule.value.length !== 2) return "Enter both ends of the range";
    if (rule.value.some((entry) => entry === "" || entry === null || entry === undefined)) {
      return "Enter both ends of the range";
    }
    return null;
  }
  if (shape === "list") {
    if (!Array.isArray(rule.value) || rule.value.length === 0) return "Enter at least one value";
    return null;
  }
  if (rule.value === "" || rule.value === null || rule.value === undefined) return "Enter a value";
  if (kind === "number" && Number.isNaN(Number(rule.value))) return "Enter a number";
  return null;
}

/**
 * Everything wrong with a draft, mirroring the compiler's own checks and the schema's bounds.
 *
 * Reported as a map rather than thrown, because a rule builder shows several problems at once and
 * an operator fixing a segment wants to see all of them. The server re-validates and its 422 is
 * what decides.
 */
export function validateSegment(
  name: string,
  description: string,
  groups: RuleGroup[],
  attributes: AttributeDefinition[],
): SegmentProblems {
  const problems: SegmentProblems = { rules: {} };

  if (name.trim() === "") problems.name = "Name is required";
  else if (name.length > MAX_NAME_LENGTH) {
    problems.name = `Name is limited to ${MAX_NAME_LENGTH} characters`;
  }
  if (description.length > MAX_DESCRIPTION_LENGTH) {
    problems.description = `Description is limited to ${MAX_DESCRIPTION_LENGTH} characters`;
  }

  groups.forEach((group, groupIndex) => {
    group.rules.forEach((rule, ruleIndex) => {
      const id = `${groupIndex}:${ruleIndex}`;
      const source = rule.field_source as FieldSource;
      const fields = fieldsForSource(source, attributes);
      const field = fields.find((candidate) => candidate.key === rule.field_key);

      if (source === "attribute" && !field) {
        problems.rules[id] = "Choose a custom attribute";
        return;
      }
      if (!field) {
        problems.rules[id] = "Choose a field";
        return;
      }
      if (!operatorsFor(source, field.kind).includes(rule.operator)) {
        problems.rules[id] = "That condition does not apply to this field";
        return;
      }

      const problem = ruleValueProblem(rule, field.kind);
      if (problem) problems.rules[id] = problem;
    });
  });

  return problems;
}

export function hasProblems(problems: SegmentProblems): boolean {
  return Boolean(problems.name || problems.description) || Object.keys(problems.rules).length > 0;
}
