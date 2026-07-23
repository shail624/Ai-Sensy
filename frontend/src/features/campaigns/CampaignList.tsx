import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useCampaigns, useHasPermission } from "@/features/campaigns/api";
import { CampaignFilters } from "@/features/campaigns/CampaignFilters";
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
 * Filtering and paging run client-side over the complete list the endpoint returns; `api.ts`
 * documents why. The consequence is honest rather than hidden: the page counts below describe the
 * whole filtered set, not just what was fetched.
 */
export function CampaignList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("campaigns:write");

  const campaigns = useCampaigns();
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

  if (campaigns.isLoading) return <Spinner label="Loading campaigns…" />;

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
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <CampaignFilters filters={query} onChange={apply} />
        {canWrite ? (
          <Link
            to="/campaigns/new"
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            New campaign
          </Link>
        ) : null}
      </div>

      {!hasCampaigns ? (
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
