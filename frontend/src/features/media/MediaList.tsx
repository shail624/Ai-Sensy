import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useHasPermission, useMediaList } from "@/features/media/api";
import { MediaFilters } from "@/features/media/MediaFilters";
import { MediaTable } from "@/features/media/MediaTable";
import { MediaUploadDialog } from "@/features/media/MediaUploadDialog";
import { librarySummary, PAGE_SIZE, selectMediaPage } from "@/features/media/selectors";
import type { MediaListQuery, MediaSort } from "@/features/media/types";
import { DEFAULT_LIST_QUERY, MEDIA_TYPES } from "@/features/media/types";
import { formatBytes, formatCount } from "@/lib/format";

const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50";

const SORTS: MediaSort[] = ["-created_at", "created_at", "name", "-byte_size", "byte_size"];

/** URL ⇄ query, so a filtered library is linkable and survives a reload — as `TaskList` does. */
function readQuery(params: URLSearchParams): MediaListQuery {
  const mediaType = params.get("type") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? DEFAULT_LIST_QUERY.q,
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    mediaType: (MEDIA_TYPES as string[]).includes(mediaType) ? mediaType : DEFAULT_LIST_QUERY.mediaType,
    sort: SORTS.includes(sort as MediaSort) ? (sort as MediaSort) : DEFAULT_LIST_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: MediaListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.mediaType) params.set("type", query.mediaType);
  if (query.sort !== DEFAULT_LIST_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * The Media Library (Doc 05 B6.1) — search, type filter, sort, pagination and per-asset actions,
 * with state held in the address bar.
 *
 * The endpoint answers with its default page of 50 newest assets plus the library's true `total`
 * (`api.ts` explains why neither can be changed from here). When the library is larger than what
 * was returned, the caption says so plainly — a filter that finds nothing may simply be looking at
 * the wrong 50 assets, and an operator needs to know that rather than conclude the file is gone.
 */
export function MediaList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [uploading, setUploading] = useState(false);
  const [showPreviews, setShowPreviews] = useState(false);

  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canWrite = useHasPermission("media:write");

  const media = useMediaList();
  const assets = useMemo(() => media.data?.data ?? [], [media.data]);
  const page = useMemo(() => selectMediaPage(assets, query), [assets, query]);
  const summary = useMemo(() => librarySummary(assets), [assets]);

  const libraryTotal = media.data?.total ?? 0;
  const truncated = libraryTotal > assets.length;
  const isFiltered = query.q !== "" || query.mediaType !== "";

  function apply(next: MediaListQuery): void {
    setSearchParams(writeQuery(next));
  }

  function goToPage(next: number): void {
    setSearchParams(writeQuery({ ...query, page: next }));
  }

  if (media.isLoading) return <Spinner label="Loading media…" />;

  if (media.isError) {
    return (
      <ErrorState message={apiErrorMessage(media.error)} onRetry={() => void media.refetch()} />
    );
  }

  return (
    <>
      {assets.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.count)} file{summary.count === 1 ? "" : "s"} ·{" "}
          {formatBytes(summary.bytes)} · {formatCount(summary.unused)} unused
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <MediaFilters filters={query} onChange={apply} />
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={showPreviews}
              onChange={(event) => setShowPreviews(event.target.checked)}
            />
            Show previews
          </label>
          {canWrite ? (
            <button
              type="button"
              onClick={() => setUploading(true)}
              className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              Upload media
            </button>
          ) : null}
        </div>
      </div>

      {showPreviews ? (
        <p className="mb-3 text-xs text-text-disabled">
          Previews download each image in full — there is no thumbnail pipeline yet.
        </p>
      ) : null}

      {assets.length === 0 ? (
        <EmptyState
          title="The library is empty"
          description={
            canWrite
              ? "Upload an image, video, audio file or document to use it in templates and messages."
              : "No media has been uploaded yet."
          }
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No files match these filters"
          description={
            truncated
              ? "Try a different name or type. Only the 50 most recent files are loaded, so an older file may not be among them."
              : "Try a different name or type."
          }
        />
      ) : (
        <>
          <MediaTable assets={page.rows} showPreviews={showPreviews} />

          <nav
            aria-label="Pagination"
            className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary"
          >
            <p>
              {isFiltered ? "Matching: " : ""}
              {formatCount(page.total)} file{page.total === 1 ? "" : "s"}
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

          {truncated ? (
            <p className="mt-2 text-xs text-text-disabled">
              The library holds {formatCount(libraryTotal)} files; the {formatCount(assets.length)}{" "}
              most recent are shown here.
            </p>
          ) : null}
        </>
      )}

      {uploading ? <MediaUploadDialog onClose={() => setUploading(false)} /> : null}
    </>
  );
}
