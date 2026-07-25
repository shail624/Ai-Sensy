import { ChevronRight, Search, SlidersHorizontal } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Skeleton } from "@/components/ui";
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
import { useAuth } from "@/lib/auth";
import { useIsCompact } from "@/lib/useMediaQuery";
import { useWorkspacePreferences } from "@/lib/workspace";

const FIELD_CLASS =
  "h-9 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

/** Table-shaped placeholder, so the page keeps its layout while the list loads. */
function LoadingRows(): JSX.Element {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-border px-4 py-3.5 last:border-0">
          <Skeleton className="h-3.5 w-48" />
          <Skeleton className="ml-auto h-5 w-24 rounded-full" />
          <Skeleton className="hidden h-5 w-24 rounded-full sm:block" />
        </div>
      ))}
    </div>
  );
}

const TH = "px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wide text-text-disabled";
const TD = "px-4 py-3 align-middle";

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
  const { user } = useAuth();
  const workspace = useWorkspacePreferences(user?.id);

  const compact = useIsCompact();
  const segments = useSegments();
  const all = useMemo(() => segments.data ?? [], [segments.data]);
  const page = useMemo(() => selectSegmentPage(all, query), [all, query]);
  const summary = useMemo(() => segmentSummary(all), [all]);

  const isFiltered = query.q !== "" || query.state !== "" || query.match !== "";

  function apply(next: Partial<SegmentListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next, page: 1 }));
  }

  if (segments.isLoading) return <LoadingRows />;

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

      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <div className="relative min-w-[220px] flex-1">
          <label htmlFor="segments-search" className="sr-only">
            Search
          </label>
          <Search
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-disabled"
          />
          <input
            id="segments-search"
            type="search"
            value={query.q}
            onChange={(event) => apply({ q: event.target.value })}
            placeholder="Name or description…"
            className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text-primary placeholder:text-text-disabled focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          />
        </div>

        <SlidersHorizontal aria-hidden className="hidden h-4 w-4 text-text-disabled sm:block" />

        <div className="flex flex-col gap-1">
            <label htmlFor="segments-state" className="sr-only">
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
            <label htmlFor="segments-match" className="sr-only">
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
            <label htmlFor="segments-sort" className="sr-only">
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

        {canWrite ? (
          <Link
            to="/segments/new"
            className="inline-flex h-9 items-center justify-center rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg shadow-sm hover:bg-accent-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
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
          {compact ? (
            <ul className="space-y-2.5">
              {page.rows.map((segment) => (
                <li
                  key={segment.id}
                  className="rounded-2xl border border-border bg-surface p-3.5 shadow-sm"
                >
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <Link
                        to={`/segments/${segment.id}`}
                        onClick={() => workspace.recordRecent({ label: segment.name, path: `/segments/${segment.id}` })}
                        className="block truncate font-semibold text-text-primary focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        {segment.name}
                      </Link>
                      {segment.description ? (
                        <p className="truncate text-xs text-text-secondary">{segment.description}</p>
                      ) : null}
                    </div>
                    <SegmentActions segment={segment} compact />
                  </div>
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <CountChip segment={segment} />
                    <RuleCountChip count={segment.rules.length} />
                    <MatchTypeChip value={segment.match_type} />
                  </div>
                  <p className="mt-2 text-xs text-text-disabled">
                    Updated {formatDate(segment.updated_at)}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-border bg-surface shadow-sm">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2">
                    <th scope="col" className={TH}>Segment</th>
                    <th scope="col" className={TH}>Size</th>
                    <th scope="col" className={`${TH} hidden lg:table-cell`}>Conditions</th>
                    <th scope="col" className={`${TH} hidden xl:table-cell`}>Logic</th>
                    <th scope="col" className={`${TH} hidden xl:table-cell`}>Updated</th>
                    <th scope="col" className={`${TH} text-right`}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {page.rows.map((segment) => (
                    <tr
                      key={segment.id}
                      className="group border-b border-border transition-colors last:border-0 hover:bg-hover"
                    >
                      <td className={TD}>
                        <div className="flex items-center gap-2">
                          <div className="min-w-0">
                            <Link
                              to={`/segments/${segment.id}`}
                              onClick={() => workspace.recordRecent({ label: segment.name, path: `/segments/${segment.id}` })}
                              className="font-semibold text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                            >
                              {segment.name}
                            </Link>
                            {segment.description ? (
                              <p className="max-w-md truncate text-xs text-text-secondary">
                                {segment.description}
                              </p>
                            ) : null}
                          </div>
                          <ChevronRight
                            aria-hidden
                            className="h-4 w-4 shrink-0 text-text-disabled opacity-0 transition-opacity group-hover:opacity-100"
                          />
                        </div>
                      </td>
                      <td className={TD}>
                        <CountChip segment={segment} />
                      </td>
                      <td className={`${TD} hidden lg:table-cell`}>
                        <RuleCountChip count={segment.rules.length} />
                      </td>
                      <td className={`${TD} hidden xl:table-cell`}>
                        <MatchTypeChip value={segment.match_type} />
                      </td>
                      <td className={`${TD} hidden text-text-secondary xl:table-cell`}>
                        {formatDate(segment.updated_at)}
                      </td>
                      <td className={`${TD} text-right`}>
                        <SegmentActions segment={segment} compact />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

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
