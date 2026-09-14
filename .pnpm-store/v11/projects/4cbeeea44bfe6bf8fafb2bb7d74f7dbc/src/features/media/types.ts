import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type MediaAsset = components["schemas"]["MediaResponse"];
export type MediaList = components["schemas"]["MediaListResponse"];
export type MediaContent = components["schemas"]["MediaContentResponse"];
export type MediaUploadBody = components["schemas"]["Body_upload_media_api_v1_media_upload_post"];

/**
 * Media type is typed `str` on the wire (Doc 04 §16), so the contract carries no enum to derive
 * from. This is the **display vocabulary** for the five kinds `storage/validation.py` defines —
 * labels and a filter list, not an API type. A value missing here renders verbatim rather than
 * being dropped.
 */
export type MediaType = "image" | "video" | "audio" | "document" | "sticker";

export const MEDIA_TYPE_LABELS: Record<MediaType, string> = {
  image: "Image",
  video: "Video",
  audio: "Audio",
  document: "Document",
  sticker: "Sticker",
};

export const MEDIA_TYPES = Object.keys(MEDIA_TYPE_LABELS) as MediaType[];

/**
 * Allowed MIME types and size ceilings per media type, mirroring `storage/validation.py`.
 *
 * These are the WhatsApp Cloud API limits: a file the platform would later fail to send is
 * rejected at the door rather than stored and discovered broken at send time. Repeating them here
 * turns a 413/415 round trip into immediate feedback at the file picker — the server re-validates
 * everything and its error is what decides.
 */
export interface MediaRule {
  mimeTypes: string[];
  maxBytes: number;
}

const MB = 1024 * 1024;

export const MEDIA_RULES: Record<MediaType, MediaRule> = {
  image: { mimeTypes: ["image/jpeg", "image/png"], maxBytes: 5 * MB },
  video: { mimeTypes: ["video/mp4", "video/3gpp"], maxBytes: 16 * MB },
  audio: {
    mimeTypes: ["audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg"],
    maxBytes: 16 * MB,
  },
  document: {
    mimeTypes: [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.ms-powerpoint",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      "text/plain",
      "text/csv",
    ],
    maxBytes: 100 * MB,
  },
  sticker: { mimeTypes: ["image/webp"], maxBytes: 500 * 1024 },
};

/** The `accept` attribute for a media type's file picker, so the OS dialog filters correctly. */
export function acceptFor(mediaType: MediaType): string {
  return MEDIA_RULES[mediaType].mimeTypes.join(",");
}

/** Which media types the browser can render inline, and how. */
export function isImageLike(mediaType: string): boolean {
  return mediaType === "image" || mediaType === "sticker";
}

/**
 * An asset is deletable only while nothing has used it — `usage_count` is what stops an in-use
 * asset being removed, and the server answers 409 (Doc 04 §16).
 */
export function isDeletable(asset: MediaAsset): boolean {
  return asset.usage_count === 0;
}

// --- List query (client-side; see `api.ts` for why) ---------------------------------------------

export type MediaSort = "-created_at" | "created_at" | "name" | "-byte_size" | "byte_size";

export interface MediaListQuery {
  q: string;
  mediaType: string;
  sort: MediaSort;
  page: number;
}

export const DEFAULT_LIST_QUERY: MediaListQuery = {
  q: "",
  mediaType: "",
  sort: "-created_at",
  page: 1,
};
