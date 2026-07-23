import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
// The administration feature owns the shared list footer; importing it keeps one implementation of
// how these lists page.
import { AdminPagination } from "@/features/admin";
import { apiErrorMessage, useHasPermission, useSegments } from "@/features/segments/api";
import { CountChip, MatchTypeChip, RuleCountChip } from "@/features/segments/SegmentBadges";
import { SegmentActions } from "@/features/segments/SegmentActions";
import type { SegmentListQuery, SegmentSort } from "@/features/segments/selectors";
import {
  DEFAULT_LIST_QUERY,
  segmentSummary,
  selectSegmentPage,
} from "@/features/segments/selectors";
import { MATCH_TYPE_LABELS, MATCH_TYPES } from "@/features/segments/types";
import { formatCount, formatDate } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORTS: SegmentSort[] = ["name", "-name", "-cached_count", "-updated_at", "-created_at"];

const SORT_LABELS: Record<SegmentSort, string> = {
  name: "Name (A–Z)",
  "-name": "Name (Z–A)",
  "-cached_count": "Largest",
  "-updated_at": "Recently changed",
  "-created_at": "Newest",
};

const STATES = ["evaluated", "stale", "empty"];

const STATE_LABELS: Record<string, string> = {
  evaluated: "Evaluated",
  stale: "Not evaluated",
  empty: "Matches nobody",
};

function readQuery(params: URLSearchParams): SegmentListQuery {
  const state = params.get("state") ?? "";
  const match = params.get("match") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? "",
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    state: STATES.includes(state) ? state : "",
    match: (MATCH_TYPES as readonly string[]).includes(match) ? match : "",
    sort: SORTS.includes(sort as SegmentSort) ? (sort as SegmentSort) : DEFAULT_LIST_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: SegmentListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.state) params.set("state", query.state);
  if (query.match) params.set("match", query.match);
  if (query.sort !== DEFAULT_LIST_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * Saved dynamic contact filters (FR-CON-10).
 *
 * `GET /segments` takes no parameters and returns the organization's complete list with its cached
 * counts, so searching, filtering, sorting and paging run over everything there is — there is no
 * page boundary to warn about here.
 */
export function SegmentList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("segments:write");

  const segments = useSegments();
  const all = useMemo(() => segments.data ?? [], [segments.data]);
  const page = useMemo(() => selectSegmentPage(all, query), [all, query]);
  const summary = useMemo(() => segmentSummary(all), [all]);

  const isFiltered = query.q !== "" || query.state !== "" || query.match !== "";

  function apply(next: Partial<SegmentListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next, page: 1 }));
  }

  if (segments.isLoading) return <Spinner label="Loading segments…" />;

  if (segments.isError) {
    return (
      <ErrorState message={apiErrorMessage(segments.error)} onRetry={() => void segments.refetch()} />
    );
  }

  return (
    <>
      {all.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.total)} segment{summary.total === 1 ? "" : "s"} ·{" "}
          {formatCount(summary.evaluated)} evaluated
          {summary.stale > 0 ? ` · ${formatCount(summary.stale)} awaiting evaluation` : ""}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
            <label htmlFor="segments-search" className="text-xs font-medium text-text-secondary">
              Search
            </label>
            <input
              id="segments-search"
              type="search"
              value={query.q}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Name or description…"
              className={FIELD_CLASS}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="segments-state" className="text-xs font-medium text-text-secondary">
              State
            </label>
            <select
              id="segments-state"
              value={query.state}
              onChange={(event) => apply({ state: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">Any state</option>
              {STATES.map((state) => (
                <option key={state} value={state}>
                  {STATE_LABELS[state]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="segments-match" className="text-xs font-medium text-text-secondary">
              Logic
            </label>
            <select
              id="segments-match"
              value={query.match}
              onChange={(event) => apply({ match: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">Any logic</option>
              {MATCH_TYPES.map((match) => (
                <option key={match} value={match}>
                  {MATCH_TYPE_LABELS[match]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="segments-sort" className="text-xs font-medium text-text-secondary">
              Sort
            </label>
            <select
              id="segments-sort"
              value={query.sort}
              onChange={(event) => apply({ sort: event.target.value as SegmentSort })}
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
          <Link
            to="/segments/new"
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            New segment
          </Link>
        ) : null}
      </div>

      {all.length === 0 ? (
        <EmptyState
          title="No segments yet"
          description={
            canWrite
              ? "A segment is a saved filter over your contacts — build one to target a campaign at it."
              : "No segments have been created yet."
          }
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No segments match these filters"
          description="Try a different name, state or logic."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Segment</th>
                  <th scope="col" className="px-3 py-2">Size</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Conditions</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Logic</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Updated</th>
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((segment) => (
                  <tr key={segment.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-3 py-2">
                      <Link
                        to={`/segments/${segment.id}`}
                        className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        {segment.name}
                      </Link>
                      {segment.description ? (
                        <p className="max-w-md truncate text-xs text-text-secondary">
                          {segment.description}
                        </p>
                      ) : null}
                      <div className="mt-1 flex flex-wrap gap-1 lg:hidden">
                        <RuleCountChip count={segment.rules.length} />
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <CountChip segment={segment} />
                    </td>
                    <td className="hidden px-3 py-2 lg:table-cell">
                      <RuleCountChip count={segment.rules.length} />
                    </td>
                    <td className="hidden px-3 py-2 xl:table-cell">
                      <MatchTypeChip value={segment.match_type} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {formatDate(segment.updated_at)}
                    </td>
                    <td className="px-3 py-2">
                      <SegmentActions segment={segment} compact />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <AdminPagination
            page={page.page}
            totalPages={page.totalPages}
            total={page.total}
            noun="segment"
            filtered={isFiltered}
            onGoTo={(next) => setSearchParams(writeQuery({ ...query, page: next }))}
          />
        </>
      )}
    </>
  );
}
