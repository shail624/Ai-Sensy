import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  usePipelines,
} from "@/features/pipelines/api";
import { PipelineActions } from "@/features/pipelines/PipelineActions";
import { DefaultChip, StageCountChip } from "@/features/pipelines/PipelineBadges";
import { PipelineFormDialog } from "@/features/pipelines/PipelineFormDialog";
import { pipelineSummary, selectPipelines } from "@/features/pipelines/selectors";
import type { PipelineListQuery, PipelineSort } from "@/features/pipelines/types";
import {
  DEFAULT_LIST_QUERY,
  orderedStages,
  SORT_LABELS,
} from "@/features/pipelines/types";
import { formatCount, formatDate } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORTS: PipelineSort[] = ["name", "-name", "-stages", "-updated_at"];
const KINDS = ["default", "custom"];
const KIND_LABELS: Record<string, string> = { default: "Default only", custom: "Custom only" };

function readQuery(params: URLSearchParams): PipelineListQuery {
  const kind = params.get("kind") ?? "";
  const sort = params.get("sort") ?? "";
  return {
    q: params.get("q") ?? "",
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    kind: KINDS.includes(kind) ? kind : "",
    sort: SORTS.includes(sort as PipelineSort) ? (sort as PipelineSort) : DEFAULT_LIST_QUERY.sort,
  };
}

function writeQuery(query: PipelineListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.kind) params.set("kind", query.kind);
  if (query.sort !== DEFAULT_LIST_QUERY.sort) params.set("sort", query.sort);
  return params;
}

/**
 * Lead pipelines (Doc 07 §19).
 *
 * `GET /lead-pipelines` takes no parameters and returns every pipeline with its stages already
 * nested and ordered, so searching, filtering and sorting run over everything there is — there is
 * no page boundary here, and no second request to fetch a pipeline's stages.
 */
export function PipelineList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [creating, setCreating] = useState(false);

  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("contacts:write");

  const pipelines = usePipelines();
  const all = useMemo(() => pipelines.data ?? [], [pipelines.data]);
  const rows = useMemo(() => selectPipelines(all, query), [all, query]);
  const summary = useMemo(() => pipelineSummary(all), [all]);
  const names = useMemo(() => all.map((pipeline) => pipeline.name), [all]);
  const currentDefault = all.find((pipeline) => pipeline.is_default)?.name;

  const isFiltered = query.q !== "" || query.kind !== "";

  function apply(next: Partial<PipelineListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next }));
  }

  if (pipelines.isLoading) return <Spinner label="Loading pipelines…" />;

  if (pipelines.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(pipelines.error)}
        onRetry={() => void pipelines.refetch()}
      />
    );
  }

  return (
    <>
      {all.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.total)} pipeline{summary.total === 1 ? "" : "s"} ·{" "}
          {formatCount(summary.stages)} stage{summary.stages === 1 ? "" : "s"}
          {summary.empty > 0 ? ` · ${formatCount(summary.empty)} with no stages` : ""}
        </p>
      ) : null}

      {all.length > 0 && !summary.hasDefault ? (
        <p role="alert" className="mb-3 rounded-md border border-warning px-3 py-2 text-sm text-warning">
          No pipeline is marked as the default. New leads have nowhere to land — mark one.
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
            <label htmlFor="pipelines-search" className="text-xs font-medium text-text-secondary">
              Search
            </label>
            <input
              id="pipelines-search"
              type="search"
              value={query.q}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Pipeline or stage name…"
              className={FIELD_CLASS}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="pipelines-kind" className="text-xs font-medium text-text-secondary">
              Kind
            </label>
            <select
              id="pipelines-kind"
              value={query.kind}
              onChange={(event) => apply({ kind: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All pipelines</option>
              {KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {KIND_LABELS[kind]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="pipelines-sort" className="text-xs font-medium text-text-secondary">
              Sort
            </label>
            <select
              id="pipelines-sort"
              value={query.sort}
              onChange={(event) => apply({ sort: event.target.value as PipelineSort })}
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

        {canWrite ? (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            New pipeline
          </button>
        ) : null}
      </div>

      {all.length === 0 ? (
        <EmptyState
          title="No pipelines"
          description={
            canWrite
              ? "A pipeline is the ordered set of stages a lead moves through. Create one to start."
              : "No pipelines have been configured yet."
          }
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No pipelines match these filters"
          description="Try a different name or kind."
        />
      ) : (
        <>
          <ul className="space-y-3">
            {rows.map((pipeline) => {
              const stages = orderedStages(pipeline);
              return (
                <li
                  key={pipeline.id}
                  className="rounded-lg border border-border bg-surface p-4 hover:border-accent"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/pipelines/${pipeline.id}`}
                          className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                        >
                          {pipeline.name}
                        </Link>
                        {pipeline.is_default ? <DefaultChip /> : null}
                        <StageCountChip count={stages.length} />
                      </div>
                      <p className="mt-1 text-xs text-text-disabled">
                        Updated {formatDate(pipeline.updated_at)}
                      </p>
                    </div>

                    <PipelineActions
                      pipeline={pipeline}
                      existingNames={names}
                      currentDefault={currentDefault}
                      compact
                    />
                  </div>

                  {stages.length > 0 ? (
                    // The stage order is what a pipeline *is*, so the list shows it inline rather
                    // than making an operator open each one to see the shape of their process.
                    <ol className="mt-3 flex flex-wrap items-center gap-1">
                      {stages.map((stage, index) => (
                        <li key={stage.id} className="flex items-center gap-1">
                          {index > 0 ? (
                            <span aria-hidden className="text-text-disabled">
                              →
                            </span>
                          ) : null}
                          <span
                            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${
                              stage.is_terminal
                                ? "border-success text-success"
                                : "border-border text-text-secondary"
                            }`}
                          >
                            {stage.name}
                          </span>
                        </li>
                      ))}
                    </ol>
                  ) : null}

                  {stages.some((stage) => stage.is_terminal) ? null : stages.length > 0 ? (
                    <p className="mt-2 text-xs text-warning">
                      No final stage — a lead in this pipeline has nowhere to finish.
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>

          <p className="mt-3 text-sm text-text-secondary">
            {isFiltered ? "Matching: " : ""}
            {formatCount(rows.length)} pipeline{rows.length === 1 ? "" : "s"}
          </p>
        </>
      )}

      {creating ? (
        <PipelineFormDialog
          existingNames={names}
          currentDefault={currentDefault}
          onClose={() => setCreating(false)}
        />
      ) : null}
    </>
  );
}
