import { Link } from "react-router-dom";

import { useMediaContent } from "@/features/media/api";
import { MediaActions } from "@/features/media/MediaActions";
import { MediaGlyph, MediaTypeChip, UsageChip } from "@/features/media/MediaBadges";
import { displayName } from "@/features/media/selectors";
import type { MediaAsset } from "@/features/media/types";
import { isImageLike } from "@/features/media/types";
import { formatBytes, formatDate, formatDuration } from "@/lib/format";

interface Props {
  assets: MediaAsset[];
  /** When on, image rows fetch their bytes so the row shows the picture instead of a glyph. */
  showPreviews: boolean;
}

/**
 * The media library table (Doc 05 B6.1).
 *
 * Previews are **off by default and opt-in**. There is no thumbnail pipeline — media processing is
 * a separate, unbuilt module — so a preview here means fetching the original file, up to 5 MB an
 * image. Rendering a page of those unasked would cost far more than the list is worth, so the
 * operator turns it on when they need to see the pictures.
 *
 * Secondary columns drop away below `md` rather than being squeezed.
 */
export function MediaTable({ assets, showPreviews }: Props): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="px-3 py-2">File</th>
            <th scope="col" className="hidden px-3 py-2 sm:table-cell">Type</th>
            <th scope="col" className="hidden px-3 py-2 md:table-cell">Size</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Dimensions</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Uploaded</th>
            <th scope="col" className="hidden px-3 py-2 xl:table-cell">Usage</th>
            <th scope="col" className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id} className="border-b border-border last:border-0 hover:bg-hover">
              <td className="px-3 py-2">
                <div className="flex items-center gap-3">
                  <MediaThumbnail asset={asset} enabled={showPreviews} />
                  <div className="min-w-0">
                    <Link
                      to={`/media/${asset.id}`}
                      className="block truncate font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    >
                      {displayName(asset)}
                    </Link>
                    <p className="truncate font-mono text-xs text-text-disabled">
                      {asset.mime_type}
                    </p>
                    <div className="mt-1 sm:hidden">
                      <MediaTypeChip value={asset.media_type} />
                    </div>
                  </div>
                </div>
              </td>
              <td className="hidden px-3 py-2 sm:table-cell">
                <MediaTypeChip value={asset.media_type} />
              </td>
              <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                {formatBytes(asset.byte_size)}
              </td>
              <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                {asset.width && asset.height
                  ? `${asset.width}×${asset.height}`
                  : asset.duration_sec
                    ? formatDuration(asset.duration_sec)
                    : "—"}
              </td>
              <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                {formatDate(asset.created_at)}
              </td>
              <td className="hidden px-3 py-2 xl:table-cell">
                <UsageChip count={asset.usage_count} />
              </td>
              <td className="px-3 py-2">
                <MediaActions asset={asset} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * A row's picture, or its type glyph.
 *
 * Only image-like assets are worth fetching for a 40-pixel square — a video or a document would
 * download in full and still render as an icon — so everything else short-circuits to the glyph
 * without a request.
 */
function MediaThumbnail({ asset, enabled }: { asset: MediaAsset; enabled: boolean }): JSX.Element {
  const wanted = enabled && isImageLike(asset.media_type);
  const content = useMediaContent(asset.id, wanted);

  if (!wanted || !content.data) return <MediaGlyph mediaType={asset.media_type} />;

  return (
    <img
      src={content.data.url}
      alt={displayName(asset)}
      className="h-9 w-9 shrink-0 rounded-md border border-border object-cover"
    />
  );
}
