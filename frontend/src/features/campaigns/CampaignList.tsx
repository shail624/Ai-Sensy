import { ChevronLeft, ChevronRight, Download, Plus, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { MANAGE_PRIMARY_ACTION } from "@/components/layout";
import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useCampaigns, useHasPermission } from "@/features/campaigns/api";
import { CampaignQuotaStrip } from "@/features/campaigns/CampaignQuotaStrip";
import { OverviewReportDialog, UserReportDialog } from "@/features/campaigns/CampaignReportDialogs";
import { CampaignTypeDialog } from "@/features/campaigns/CampaignTypeDialog";
import { CampaignSavedViews } from "@/features/campaigns/CampaignSavedViews";
import { CampaignTable } from "@/features/campaigns/CampaignTable";
import { formatCount } from "@/features/campaigns/format";
import { PAGE_SIZE, selectCampaignPage } from "@/features/campaigns/selectors";
import type { CampaignListQuery, CampaignSort } from "@/features/campaigns/types";
import { CAMPAIGN_STATUSES, DEFAULT_LIST_QUERY } from "@/features/campaigns/types";

/** The reference's tabs, mapped onto the statuses a campaign moves through. */
const CATEGORY_TABS: { label: string; status: string }[] = [
  { label: "All", status: "" },
  { label: "Scheduled", status: "scheduled" },
  { label: "Running", status: "running" },
  { label: "Completed", status: "completed" },
  { label: "Drafts", status: "draft" },
];

const REPORT_OUTLINE =
  "inline-flex h-9 items-center gap-1.5 rounded-md border border-[rgba(10,71,76,0.5)] px-3 text-sm font-medium text-[var(--color-nav-bg)] hover:bg-[#ebf5f3] dark:text-accent";
const REPORT_SOLID =
  "inline-flex h-9 items-center gap-1.5 rounded-md bg-[var(--color-nav-bg)] px-3 text-sm font-medium text-white hover:bg-[#08393d]";

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
  const [choosing, setChoosing] = useState(false);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [report, setReport] = useState<"user" | "overview" | null>(null);

  const campaigns = useCampaigns(true, { q: query.q || undefined, status: query.status || undefined });
  const page = useMemo(
    () => selectCampaignPage(campaigns.data ?? [], query, pageSize),
    [campaigns.data, query, pageSize],
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
      {choosing ? <CampaignTypeDialog onClose={() => setChoosing(false)} /> : null}
      <div className="mb-4 space-y-4">
        <CampaignQuotaStrip
          action={
            canWrite ? (
              <button type="button" aria-label="Launch campaign" onClick={() => setChoosing(true)} className={MANAGE_PRIMARY_ACTION}>
                <Plus aria-hidden className="mr-1.5 h-4 w-4" /> Launch
              </button>
            ) : null
          }
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex h-[46px] w-full max-w-[420px] items-center gap-3 rounded-[8px] bg-[#f0f0f0] px-4 dark:bg-surface-2">
            <Search aria-hidden className="h-5 w-5 text-black/60" />
            <input
              type="search"
              value={query.q}
              onChange={(event) => apply({ ...query, q: event.target.value, page: 1 })}
              placeholder="Search by campaign name"
              aria-label="Search campaigns"
              className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
            />
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-nav-bg)] disabled:opacity-50 dark:text-accent"
            disabled={campaigns.isFetching}
            onClick={() => void campaigns.refetch()}
          >
            <RefreshCw aria-hidden className={`h-4 w-4 ${campaigns.isFetching ? "animate-spin" : ""}`} />
            {campaigns.isFetching ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        <div role="tablist" aria-label="Campaign categories" className="flex overflow-x-auto border-b border-[#e0e0e0] dark:border-border">
          {CATEGORY_TABS.map((tab) => {
            const active = query.status === tab.status;
            return (
              <button
                key={tab.label}
                type="button"
                role="tab"
                aria-selected={active}
                className={`min-w-[110px] flex-1 border-b-[3px] px-4 py-3 text-sm font-medium transition-colors ${
                  active
                    ? "border-[var(--color-nav-bg)] text-[var(--color-nav-bg)] dark:text-accent"
                    : "border-transparent text-[#6e6e6e] hover:text-[var(--color-nav-bg)]"
                }`}
                onClick={() => apply({ ...query, status: tab.status, page: 1 })}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {canExport ? (
          <div className="flex flex-wrap justify-end gap-2">
            <Link to="/downloads?category=campaigns" className={REPORT_OUTLINE}>
              <Download aria-hidden className="h-4 w-4" /> Report downloads
            </Link>
            <button type="button" onClick={() => setReport("user")} className={REPORT_SOLID}>
              <Download aria-hidden className="h-4 w-4" /> User Report
            </button>
            <button type="button" onClick={() => setReport("overview")} className={REPORT_SOLID}>
              <Download aria-hidden className="h-4 w-4" /> Overview Report
            </button>
          </div>
        ) : null}
      </div>

      {report === "user" ? <UserReportDialog campaigns={campaigns.data ?? []} onClose={() => setReport(null)} /> : null}
      {report === "overview" ? <OverviewReportDialog onClose={() => setReport(null)} /> : null}

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
            className="mt-3 flex flex-wrap items-center justify-center gap-6 text-sm text-[#4a4a4a] dark:text-text-secondary"
          >
            <label className="flex items-center gap-2">
              Rows per page:
              <select
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value));
                  goToPage(1);
                }}
                className="rounded-md bg-transparent px-1 text-sm"
              >
                {[10, 25, 50].map((size) => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </label>
            <p>
              {page.total === 0 ? 0 : (page.page - 1) * pageSize + 1}-{Math.min(page.page * pageSize, page.total)} of {formatCount(page.total)}
            </p>
            <div className="flex items-center gap-1">
              <button
                type="button"
                aria-label="Previous page"
                className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-hover disabled:opacity-30"
                disabled={page.page <= 1}
                onClick={() => goToPage(page.page - 1)}
              >
                <ChevronLeft aria-hidden className="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Next page"
                className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-hover disabled:opacity-30"
                disabled={page.page >= page.totalPages}
                onClick={() => goToPage(page.page + 1)}
              >
                <ChevronRight aria-hidden className="h-5 w-5" />
              </button>
            </div>
          </nav>
        </>
      )}
    </>
  );
}
