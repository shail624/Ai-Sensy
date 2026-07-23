import { ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useMediaContent } from "@/features/media/api";
import { MediaGlyph } from "@/features/media/MediaBadges";
import { displayName } from "@/features/media/selectors";
import type { MediaAsset } from "@/features/media/types";
import { formatBytes } from "@/lib/format";

/**
 * The asset itself, rendered by the browser.
 *
 * The bytes are reached through a **signed, expiring URL** rather than an authenticated fetch: the
 * signature is the credential, so the URL can go straight into an `<img>`/`<video>`/`<audio>` `src`
 * with no token in the markup. The URL is re-issued before it expires (see `useMediaContent`), so
 * a page left open does not decay into a broken image.
 *
 * There is no thumbnail or transcode pipeline — media processing is a separate module that is not
 * built — so every preview here is the original file. That is fine for one asset on a detail page,
 * and is exactly why the list does not render previews by default.
 */
export function MediaPreview({ asset }: { asset: MediaAsset }): JSX.Element {
  const content = useMediaContent(asset.id);

  if (content.isLoading) return <Spinner label="Preparing preview…" />;

  if (content.isError || !content.data) {
    return (
      <ErrorState
        message={apiErrorMessage(content.error)}
        onRetry={() => void content.refetch()}
      />
    );
  }

  return <MediaRenderer asset={asset} url={content.data.url} />;
}

/**
 * The renderer for one asset kind. Split out from the fetching so it can be exercised — and
 * reused — without a signed-URL round trip.
 */
export function MediaRenderer({ asset, url }: { asset: MediaAsset; url: string }): JSX.Element {
  const name = displayName(asset);

  if (asset.media_type === "image" || asset.media_type === "sticker") {
    return (
      <div className="flex justify-center rounded-md border border-border bg-surface-2 p-3">
        <img
          src={url}
          alt={name}
          className="max-h-[28rem] max-w-full rounded object-contain"
          // A sticker is small and transparent; a checkerboard would be noise, so it sits on the
          // surface tone like every other asset.
        />
      </div>
    );
  }

  if (asset.media_type === "video") {
    return (
      <div className="rounded-md border border-border bg-surface-2 p-3">
        {/* No caption track: captions are not part of the asset model — the file is whatever the
            operator uploaded, and inventing an empty track would claim otherwise. */}
        <video src={url} controls preload="metadata" className="max-h-[28rem] w-full rounded">
          Your browser cannot play this video. Download it instead.
        </video>
      </div>
    );
  }

  if (asset.media_type === "audio") {
    return (
      <div className="rounded-md border border-border bg-surface-2 p-3">
        <audio src={url} controls preload="metadata" className="w-full">
          Your browser cannot play this audio. Download it instead.
        </audio>
      </div>
    );
  }

  // Documents: browsers render PDFs inline and nothing else, so anything else is offered for
  // download rather than shown in a viewer that would just prompt a download anyway.
  if (asset.mime_type === "application/pdf") {
    return (
      <div className="rounded-md border border-border bg-surface-2 p-3">
        <object data={url} type="application/pdf" className="h-[28rem] w-full rounded">
          <p className="p-4 text-sm text-text-secondary">
            This browser cannot display the PDF inline.{" "}
            <a href={url} className="text-accent hover:underline">
              Open it in a new tab
            </a>
            .
          </p>
        </object>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border bg-surface-2 p-6">
      <MediaGlyph mediaType={asset.media_type} large />
      <p className="text-sm text-text-primary">{name}</p>
      <p className="text-xs text-text-secondary">
        {asset.mime_type} · {formatBytes(asset.byte_size)}
      </p>
      <p className="text-xs text-text-disabled">
        This file type cannot be previewed in a browser. Download it to open it.
      </p>
    </div>
  );
}
