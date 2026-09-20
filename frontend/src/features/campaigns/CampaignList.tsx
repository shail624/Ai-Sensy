import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useCampaigns, useHasPermission } from "@/features/campaigns/api";
import { CampaignFilters } from "@/features/campaigns/CampaignFilters";
import { CampaignSavedViews } from "@/features/campaigns/CampaignSavedViews";
import { CampaignTable } from "@/features/campaigns/CampaignTable";
import { formatCount } from "@/features/campaigns/format";
import { PAGE_SIZE, selectCampaignPage } from "@/features/campaigns/selectors";
import type { CampaignListQuery, CampaignSort } from "@/features/campaigns/types";
import { CAMPAIGN_STATUSES, DEFAULT_LIST_QUERY } from "@/features/campaigns/types";

const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50";

const SORTS: CampaignSort[] = ["-created_at", "created_at", "name", "-name", "-total_recipients"];

/** URL ⇄ query, so a filtered list is linkable and survives a reload — as `TaskList` does. */
function readQuery(params: URLSearchParams): CampaignListQuery {
  const status = params.get("status") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? DEFAULT_LIST_QUERY.q,
    // Anything not in the known vocabulary is ignored rather than sent on to filter everything out.
    status: CAMPAIGN_STATUSES.includes(status) ? status : DEFAULT_LIST_QUERY.status,
    sort: SORTS.includes(sort as CampaignSort) ? (sort as CampaignSort) : DEFAULT_LIST_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: CampaignListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (query.sort !== DEFAULT_LIST_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * The Campaigns module (Doc 05 B4.1) — search, status filter, sort, pagination and the per-row
 * action set, with state held in the address bar.
 *
 * Search and status are server filters; existing sorting and paging remain local.
 */
export function CampaignList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("campaigns:write");
  const canExport = useHasPermission("campaigns:export");

  const campaigns = useCampaigns(true, { q: query.q || undefined, status: query.status || undefined });
  const page = useMemo(
    () => selectCampaignPage(campaigns.data ?? [], query),
    [campaigns.data, query],
  );

  const hasCampaigns = (campaigns.data?.length ?? 0) > 0;
  const isFiltered = query.q !== "" || query.status !== "";

  function apply(next: CampaignListQuery): void {
    setSearchParams(writeQuery(next));
  }

  function goToPage(next: number): void {
    setSearchParams(writeQuery({ ...query, page: next }));
  }

  if (campaigns.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(campaigns.error)}
        onRetry={() => void campaigns.refetch()}
      />
    );
  }

  return (
    <>
      <div className="mb-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border">
          <div role="tablist" aria-label="Campaign categories" className="flex items-center gap-1">
            <button
              type="button"
              role="tab"
              aria-selected={query.status === ""}
              className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                query.status === ""
                  ? "border-accent text-text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
              onClick={() => apply({ ...query, status: "", page: 1 })}
            >
              All
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={query.status === "scheduled"}
              className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                query.status === "scheduled"
                  ? "border-accent text-text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
              onClick={() => apply({ ...query, status: "scheduled", page: 1 })}
            >
              Scheduled
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 pb-2">
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={campaigns.isFetching}
              onClick={() => void campaigns.refetch()}
            >
              {campaigns.isFetching ? "Refreshing…" : "Refresh"}
            </button>
            {canExport ? (
              <Link to="/downloads?category=campaigns" className={BUTTON_CLASS}>
                Report downloads
              </Link>
            ) : null}
            {canWrite ? (
              <Link
                to="/campaigns/new"
                className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                Launch campaign
              </Link>
            ) : null}
          </div>
        </div>

        <CampaignFilters filters={query} onChange={apply} />
      </div>

      <CampaignSavedViews query={query} onApply={apply} />

      {campaigns.isLoading ? (
        <Spinner label="Loading campaigns…" />
      ) : !hasCampaigns && !isFiltered ? (
        <EmptyState
          title="No campaigns yet"
          description={
            canWrite
              ? "Create your first campaign to send a template to a segment, a set of tags, or a list of contacts."
              : "No campaigns have been created yet."
          }
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No campaigns match these filters"
          description="Try a different name or status."
        />
      ) : (
        <>
          <CampaignTable campaigns={page.rows} />

          <nav
            aria-label="Pagination"
            className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary"
          >
            <p>
              {isFiltered ? "Matching: " : ""}
              {formatCount(page.total)} campaign{page.total === 1 ? "" : "s"}
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
