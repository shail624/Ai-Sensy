import type { MediaAsset, MediaListQuery, MediaSort, MediaType } from "@/features/media/types";
import { MEDIA_RULES } from "@/features/media/types";

/** Rows per page for the client-side list (see `useMediaList` for why paging lives here). */
export const PAGE_SIZE = 25;

/** A file with no name still needs something stable to sort and search by. */
export function displayName(asset: MediaAsset): string {
  return asset.file_name ?? `${asset.media_type}-${asset.sha256.slice(0, 12)}`;
}

function byName(a: MediaAsset, b: MediaAsset): number {
  return displayName(a).localeCompare(displayName(b));
}

const COMPARATORS: Record<MediaSort, (a: MediaAsset, b: MediaAsset) => number> = {
  "-created_at": (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  created_at: (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
  name: byName,
  "-byte_size": (a, b) => b.byte_size - a.byte_size,
  byte_size: (a, b) => a.byte_size - b.byte_size,
};

/**
 * Case-insensitive match on the file name — the field the server's `q` filters on — widened to the
 * content hash, because an operator chasing a specific asset usually has its id or digest to hand
 * rather than a filename the uploader chose.
 */
export function matchesSearch(asset: MediaAsset, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    displayName(asset).toLowerCase().includes(needle) ||
    asset.sha256.toLowerCase().startsWith(needle) ||
    asset.id.toLowerCase().startsWith(needle)
  );
}

export function filterMedia(assets: MediaAsset[], query: MediaListQuery): MediaAsset[] {
  return assets.filter(
    (asset) =>
      matchesSearch(asset, query.q) &&
      (query.mediaType === "" || asset.media_type === query.mediaType),
  );
}

export function sortMedia(assets: MediaAsset[], sort: MediaSort): MediaAsset[] {
  return [...assets].sort(COMPARATORS[sort]);
}

export interface MediaPage {
  rows: MediaAsset[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, in that order, so the page numbers describe the filtered set. */
export function selectMediaPage(assets: MediaAsset[], query: MediaListQuery): MediaPage {
  const matched = sortMedia(filterMedia(assets, query), query.sort);
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * PAGE_SIZE;
  return {
    rows: matched.slice(start, start + PAGE_SIZE),
    total: matched.length,
    totalPages,
    page,
  };
}

export interface LibrarySummary {
  count: number;
  bytes: number;
  /** Assets nothing has used yet — the ones that can still be deleted. */
  unused: number;
}

/** Headline figures for the list header, so the library's shape reads at a glance. */
export function librarySummary(assets: MediaAsset[]): LibrarySummary {
  return {
    count: assets.length,
    bytes: assets.reduce((total, asset) => total + asset.byte_size, 0),
    unused: assets.filter((asset) => asset.usage_count === 0).length,
  };
}

// --- Upload validation --------------------------------------------------------------------------

export interface UploadProblem {
  field: "media_type" | "file";
  message: string;
}

/**
 * The first thing wrong with a chosen file, or `null`.
 *
 * Mirrors `storage/validation.py`, in the same order it checks: the media type must be known, the
 * file non-empty, its MIME type allowed for that type, and its size within the ceiling. Checking
 * here means a 100 MB video is refused at the file picker rather than after being uploaded — the
 * server re-validates all of it and its 413/415/422 is what decides.
 */
export function validateUpload(file: File | null, mediaType: MediaType | ""): UploadProblem | null {
  if (!mediaType) return { field: "media_type", message: "Choose what kind of file this is." };
  const rule = MEDIA_RULES[mediaType];
  if (!rule) return { field: "media_type", message: "Unknown media type." };
  if (!file) return { field: "file", message: "Choose a file." };
  if (file.size <= 0) return { field: "file", message: "That file is empty." };

  // A browser reports no type for some files; the server decides in that case rather than the UI.
  if (file.type && !rule.mimeTypes.includes(file.type)) {
    return {
      field: "file",
      message: `${file.type} is not allowed for ${mediaType}. Allowed: ${rule.mimeTypes.join(", ")}.`,
    };
  }
  if (file.size > rule.maxBytes) {
    return {
      field: "file",
      message: `This file is larger than the ${formatLimit(rule.maxBytes)} limit for ${mediaType}.`,
    };
  }
  return null;
}

/** Limits are binary and whole, so they read the way the rule is written (5 MB, 500 KB). */
export function formatLimit(maxBytes: number): string {
  const MB = 1024 * 1024;
  return maxBytes >= MB ? `${Math.round(maxBytes / MB)} MB` : `${Math.round(maxBytes / 1024)} KB`;
}

/**
 * The media type a browser-reported MIME type belongs to, or `null` when nothing claims it.
 *
 * Used to preselect the type from the chosen file, so the common case needs one action instead of
 * two. `image/webp` belongs to `sticker` and nothing else, so the mapping is unambiguous.
 */
export function mediaTypeForMime(mime: string): MediaType | null {
  for (const [mediaType, rule] of Object.entries(MEDIA_RULES)) {
    if (rule.mimeTypes.includes(mime)) return mediaType as MediaType;
  }
  return null;
}
