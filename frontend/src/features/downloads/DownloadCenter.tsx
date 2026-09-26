import { Download, FileClock, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Pagination, Spinner } from "@/components/ui";
import { apiErrorMessage, useDownloads } from "@/features/downloads/api";
import type {
  DownloadCategory,
  DownloadItem,
  DownloadQuery,
  DownloadStatus,
} from "@/features/downloads/types";
import {
  DOWNLOAD_STATUSES,
  DOWNLOAD_STATUS_LABELS,
} from "@/features/downloads/types";
import { formatCount, formatDateTime } from "@/lib/format";

const FIELD_CLASS =
  "rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

const CATEGORIES: { value: DownloadCategory; label: string }[] = [
  { value: "all", label: "All downloads" },
  { value: "contacts", label: "Contact exports" },
  { value: "analytics", label: "Analytics reports" },
  { value: "chat_history", label: "Chat transcripts" },
  { value: "campaigns", label: "Campaign results" },
];

function readFilters(params: URLSearchParams): Omit<DownloadQuery, "cursor"> {
  const category = params.get("category") ?? "all";
  const status = params.get("status") ?? "all";
  return {
    category: CATEGORIES.some((option) => option.value === category)
      ? (category as DownloadCategory)
      : "all",
    status: (["all", ...DOWNLOAD_STATUSES] as string[]).includes(status)
      ? (status as DownloadStatus)
      : "all",
  };
}

function writeFilters(filters: Omit<DownloadQuery, "cursor">): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.category !== "all") params.set("category", filters.category);
  if (filters.status !== "all") params.set("status", filters.status);
  return params;
}

function tone(status: string): "neutral" | "info" | "success" | "danger" | "warning" {
  if (status === "ready") return "success";
  if (status === "failed") return "danger";
  if (status === "expired") return "warning";
  if (status === "processing") return "info";
  return "neutral";
}

function StatusBadge({ status }: { status: string }): JSX.Element {
  const label = DOWNLOAD_STATUS_LABELS[status as DownloadStatus] ?? status;
  return <Badge tone={tone(status)} dot={status === "processing"}>{label}</Badge>;
}

function DownloadAction({ item }: { item: DownloadItem }): JSX.Element {
  if (item.status === "ready" && item.download_url) {
    return (
      <a
        href={item.download_url}
        className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <Download aria-hidden className="h-4 w-4" />
        Download
      </a>
    );
  }
  if (item.status === "failed") {
    return <span className="text-xs font-medium text-danger">Generate again from source</span>;
  }
  if (item.status === "expired") {
    return <span className="text-xs text-text-disabled">Link expired</span>;
  }
  return <span className="text-xs text-text-secondary">Preparing…</span>;
}

/** Unified AiSensy-style history for every export produced by the shared artifact pipeline. */
export function DownloadCenter(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const [cursors, setCursors] = useState<string[]>([]);
  const query = { ...filters, cursor: cursors.at(-1) };
  const downloads = useDownloads(query);
  const rows = downloads.data?.data ?? [];
  const page = downloads.data?.page;

  // Browser back/forward may restore a different URL filter without going through `apply`.
  useEffect(() => setCursors([]), [filters.category, filters.status]);

  function apply(next: Partial<typeof filters>): void {
    const updated = { ...filters, ...next };
    setCursors([]);
    setSearchParams(writeFilters(updated));
  }

  function nextPage(): void {
    const nextCursor = page?.next_cursor;
    if (nextCursor) setCursors((current) => [...current, nextCursor]);
  }

  function previousPage(): void {
    setCursors((current) => current.slice(0, -1));
  }

  if (downloads.isLoading) return <Spinner label="Loading downloads…" />;
  if (downloads.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(downloads.error)}
        onRetry={() => void downloads.refetch()}
      />
    );
  }

  const filtered = filters.category !== "all" || filters.status !== "all";

  return (
    <section aria-label="Download history">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium text-text-secondary">
            Type
            <select
              aria-label="Download type"
              className={FIELD_CLASS}
              value={filters.category}
              onChange={(event) => apply({ category: event.target.value as DownloadCategory })}
            >
              {CATEGORIES.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-text-secondary">
            Status
            <select
              aria-label="Download status"
              className={FIELD_CLASS}
              value={filters.status}
              onChange={(event) => apply({ status: event.target.value as DownloadStatus })}
            >
              <option value="all">All statuses</option>
              {DOWNLOAD_STATUSES.map((status) => (
                <option key={status} value={status}>{DOWNLOAD_STATUS_LABELS[status]}</option>
              ))}
            </select>
          </label>
        </div>
        <Button
          variant="secondary"
          size="sm"
          loading={downloads.isFetching}
          leftIcon={<RefreshCw aria-hidden className="h-4 w-4" />}
          onClick={() => void downloads.refetch()}
        >
          Refresh
        </Button>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          icon={<FileClock aria-hidden className="h-6 w-6" />}
          title={
            cursors.length > 0
              ? "No more downloads on this page"
              : filtered
                ? "No downloads match these filters"
                : "No downloads yet"
          }
          description={
            cursors.length > 0
              ? "Return to the previous page to continue browsing your history."
              : filtered
              ? "Try another type or status."
                : "Contact exports, analytics reports, chat transcripts and campaign results will appear here as soon as you create them."
          }
          action={
            cursors.length > 0 ? (
              <Button variant="secondary" onClick={previousPage}>Previous page</Button>
            ) : filtered ? (
              <Button variant="secondary" onClick={() => apply({ category: "all", status: "all" })}>
                Clear filters
              </Button>
            ) : (
              <Link className="text-sm font-semibold text-accent hover:underline" to="/analytics">
                Create an analytics report
              </Link>
            )
          }
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-4 py-3">File</th>
                  <th scope="col" className="px-4 py-3">Status</th>
                  <th scope="col" className="hidden px-4 py-3 sm:table-cell">Rows</th>
                  <th scope="col" className="hidden px-4 py-3 lg:table-cell">Created</th>
                  <th scope="col" className="hidden px-4 py-3 xl:table-cell">Available until</th>
                  <th scope="col" className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-text-primary">{item.name}</p>
                      <p className="mt-0.5 text-xs uppercase text-text-secondary">
                        {item.category} · {item.format}
                      </p>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                    <td className="hidden px-4 py-3 text-text-secondary sm:table-cell">
                      {formatCount(item.row_count)}
                    </td>
                    <td className="hidden px-4 py-3 text-text-secondary lg:table-cell">
                      {formatDateTime(item.created_at)}
                    </td>
                    <td className="hidden px-4 py-3 text-text-secondary xl:table-cell">
                      {formatDateTime(item.expires_at)}
                    </td>
                    <td className="px-4 py-3 text-right"><DownloadAction item={item} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            label="Download history pagination"
            hasPrevious={cursors.length > 0}
            hasNext={page?.has_more ?? false}
            busy={downloads.isFetching}
            onPrevious={previousPage}
            onNext={nextPage}
            summary={
              <span>
                {formatCount(page?.total)} download{page?.total === 1 ? "" : "s"}
                {cursors.length > 0 ? ` · page ${cursors.length + 1}` : ""}
              </span>
            }
          />
        </>
      )}
    </section>
  );
}
