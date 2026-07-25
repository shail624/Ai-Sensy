import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useSyncTemplates,
  useTemplates,
} from "@/features/templates/api";
import { TemplateFilters } from "@/features/templates/TemplateFilters";
import { TemplateTable } from "@/features/templates/TemplateTable";
import {
  availableLanguages,
  PAGE_SIZE,
  registryCounts,
  selectTemplatePage,
} from "@/features/templates/selectors";
import type { TemplateListQuery, TemplateSort } from "@/features/templates/types";
import { CATEGORIES, DEFAULT_LIST_QUERY, STATUSES } from "@/features/templates/types";
import { formatCount } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { useWorkspacePreferences } from "@/lib/workspace";

const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50";

const SORTS: TemplateSort[] = ["-created_at", "created_at", "name", "-name", "-updated_at"];

/** URL ⇄ query, so a filtered registry is linkable and survives a reload — as `TaskList` does. */
function readQuery(params: URLSearchParams): TemplateListQuery {
  const status = params.get("status") ?? "";
  const category = params.get("category") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? DEFAULT_LIST_QUERY.q,
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    status: STATUSES.includes(status) ? status : DEFAULT_LIST_QUERY.status,
    category: (CATEGORIES as string[]).includes(category) ? category : DEFAULT_LIST_QUERY.category,
    language: params.get("language") ?? DEFAULT_LIST_QUERY.language,
    sort: SORTS.includes(sort as TemplateSort) ? (sort as TemplateSort) : DEFAULT_LIST_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: TemplateListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (query.category) params.set("category", query.category);
  if (query.language) params.set("language", query.language);
  if (query.sort !== DEFAULT_LIST_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * The Templates module (Doc 05 B5.1) — search, approval-status/category/language filters, sort,
 * pagination and the per-row action set, with state held in the address bar.
 *
 * Filtering and paging run client-side over the complete list the endpoint returns; `api.ts`
 * documents why. The counts below therefore describe the whole filtered registry, not a fetched
 * window.
 */
export function TemplateList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("templates:write");
  const canSync = useHasPermission("templates:sync");
  const { user } = useAuth();
  const workspace = useWorkspacePreferences(user?.id);

  const templates = useTemplates();
  const sync = useSyncTemplates();

  const rows = useMemo(() => templates.data ?? [], [templates.data]);
  const page = useMemo(() => selectTemplatePage(rows, query), [rows, query]);
  const languages = useMemo(() => availableLanguages(rows), [rows]);
  const counts = useMemo(() => registryCounts(rows), [rows]);

  const isFiltered =
    query.q !== "" || query.status !== "" || query.category !== "" || query.language !== "";

  function apply(next: TemplateListQuery): void {
    setSearchParams(writeQuery(next));
  }

  function goToPage(next: number): void {
    setSearchParams(writeQuery({ ...query, page: next }));
  }

  if (templates.isLoading) return <Spinner label="Loading templates…" />;

  if (templates.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(templates.error)}
        onRetry={() => void templates.refetch()}
      />
    );
  }

  return (
    <>
      {rows.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(counts.sendable)} of {formatCount(counts.total)} templates can be broadcast
          {counts.pending > 0 ? ` · ${formatCount(counts.pending)} awaiting review` : ""}
          {counts.rejected > 0 ? ` · ${formatCount(counts.rejected)} rejected` : ""}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <TemplateFilters filters={query} languages={languages} onChange={apply} />
        <div className="flex flex-wrap items-center gap-2">
          {canSync ? (
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={sync.isPending}
              onClick={() => sync.mutate(undefined)}
            >
              {sync.isPending ? "Starting sync…" : "Sync from Meta"}
            </button>
          ) : null}
          {canWrite ? (
            <Link
              to="/templates/new"
              className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              New template
            </Link>
          ) : null}
        </div>
      </div>

      {sync.isSuccess ? (
        <p className="mb-3 rounded-md border border-info px-3 py-2 text-sm text-info">
          Sync started. Meta is reconciled in the background — approval statuses update here once it
          finishes.
        </p>
      ) : null}
      {sync.error ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(sync.error)} />
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState
          title="No templates yet"
          description={
            canSync
              ? "Sync from Meta to pull in templates that already exist, or create one here."
              : canWrite
                ? "Create a template and submit it to Meta for approval."
                : "No templates have been created yet."
          }
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No templates match these filters"
          description="Try a different name, status, category or language."
        />
      ) : (
        <>
          <TemplateTable
            templates={page.rows}
            favoritePaths={workspace.favorites}
            onToggleFavorite={workspace.toggleFavorite}
          />

          <nav
            aria-label="Pagination"
            className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary"
          >
            <p>
              {isFiltered ? "Matching: " : ""}
              {formatCount(page.total)} template{page.total === 1 ? "" : "s"}
              {page.totalPages > 1
                ? ` · page ${page.page} of ${page.totalPages} (${PAGE_SIZE} per page)`
                : ""}
            </p>
            {page.totalPages > 1 ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className={BUTTON_CLASS}
                  disabled={page.page <= 1}
                  onClick={() => goToPage(page.page - 1)}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className={BUTTON_CLASS}
                  disabled={page.page >= page.totalPages}
                  onClick={() => goToPage(page.page + 1)}
                >
                  Next
                </button>
              </div>
            ) : null}
          </nav>
        </>
      )}
    </>
  );
}
