import type { MediaType } from "@/features/media/types";
import { MEDIA_TYPE_LABELS } from "@/features/media/types";

const TYPE_TONE: Record<string, string> = {
  image: "border-info text-info",
  video: "border-accent text-accent",
  audio: "border-warning text-warning",
  document: "border-border text-text-secondary",
  sticker: "border-success text-success",
};

/** Glyphs stand in for a thumbnail wherever the bytes are not fetched. */
export const TYPE_GLYPH: Record<string, string> = {
  image: "🖼",
  video: "▶",
  audio: "🔊",
  document: "📄",
  sticker: "🏷",
};

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function MediaTypeChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(TYPE_TONE[value] ?? "border-border text-text-primary")}>
      {MEDIA_TYPE_LABELS[value as MediaType] ?? value}
    </span>
  );
}

/**
 * How many messages have used this asset.
 *
 * It is not decoration: `usage_count` is what stops an in-use asset being deleted, so an asset at
 * zero is labelled "Unused" — the state in which it can still be removed.
 */
export function UsageChip({ count }: { count: number }): JSX.Element {
  if (count === 0) {
    return <span className={chip("border-border text-text-disabled")}>Unused</span>;
  }
  return (
    <span className={chip("border-success text-success")}>
      Used in {count} message{count === 1 ? "" : "s"}
    </span>
  );
}

/** A media asset's own icon, sized for a table cell or a detail header. */
export function MediaGlyph({ mediaType, large }: { mediaType: string; large?: boolean }): JSX.Element {
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-md border border-border bg-surface-2 ${
        large ? "h-16 w-16 text-2xl" : "h-9 w-9 text-base"
      }`}
    >
      {TYPE_GLYPH[mediaType] ?? "📎"}
    </span>
  );
}
