import { useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useMediaAsset } from "@/features/media/api";
import { MediaActions } from "@/features/media/MediaActions";
import { MediaTypeChip, UsageChip } from "@/features/media/MediaBadges";
import { MediaPreview } from "@/features/media/MediaPreview";
import { displayName } from "@/features/media/selectors";
import type { MediaAsset } from "@/features/media/types";
import { formatBytes, formatDateTime, formatDuration, UNKNOWN } from "@/lib/format";

/**
 * The media detail surface (Doc 05 B6.1) — the asset rendered, its metadata, where it is used, and
 * the actions that act on it.
 */
export function MediaDetail({ mediaId }: { mediaId: string }): JSX.Element {
  const navigate = useNavigate();
  const media = useMediaAsset(mediaId);

  if (media.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading file…" />
      </PageContainer>
    );
  }

  if (media.isError || !media.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Media", to: "/media" }, { label: "File" }]} />
        <ErrorState message={apiErrorMessage(media.error)} onRetry={() => void media.refetch()} />
      </PageContainer>
    );
  }

  const asset = media.data;

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Media", to: "/media" }, { label: displayName(asset) }]} />
      <PageHeader
        title={displayName(asset)}
        description={`${asset.mime_type} · ${formatBytes(asset.byte_size)}`}
        actions={<MediaActions asset={asset} onDeleted={() => navigate("/media")} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <MediaTypeChip value={asset.media_type} />
        <UsageChip count={asset.usage_count} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Section title="Preview">
          <MediaPreview asset={asset} />
        </Section>

        <div className="space-y-4">
          <MetadataSection asset={asset} />
          <UsageSection asset={asset} />
        </div>
      </div>
    </PageContainer>
  );
}

/** Everything the registry records about the file, including the identifiers other systems use. */
function MetadataSection({ asset }: { asset: MediaAsset }): JSX.Element {
  return (
    <Section title="File details">
      <dl>
        <DefinitionRow label="Media ID">
          <span className="break-all font-mono text-xs">{asset.id}</span>
        </DefinitionRow>
        <DefinitionRow label="File name">{asset.file_name ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="MIME type">
          <span className="font-mono text-xs">{asset.mime_type}</span>
        </DefinitionRow>
        <DefinitionRow label="Size">{formatBytes(asset.byte_size)}</DefinitionRow>
        {asset.width && asset.height ? (
          <DefinitionRow label="Dimensions">
            {asset.width} × {asset.height} px
          </DefinitionRow>
        ) : null}
        {asset.duration_sec ? (
          <DefinitionRow label="Duration">{formatDuration(asset.duration_sec)}</DefinitionRow>
        ) : null}
        <DefinitionRow label="Uploaded">{formatDateTime(asset.created_at)}</DefinitionRow>
        <DefinitionRow label="Storage">{asset.storage_backend}</DefinitionRow>
        <DefinitionRow label="SHA-256">
          <span className="break-all font-mono text-xs">{asset.sha256}</span>
        </DefinitionRow>
      </dl>
      <p className="mt-3 text-xs text-text-disabled">
        The library stores each distinct file once, keyed by its SHA-256 — uploading identical bytes
        returns this same asset rather than a second copy.
      </p>
    </Section>
  );
}

/**
 * How often the asset has been used, and what that means.
 *
 * The count is what it is — there is no endpoint listing *which* messages used it, so this reports
 * the number and what it governs rather than implying a drill-down that does not exist.
 */
function UsageSection({ asset }: { asset: MediaAsset }): JSX.Element {
  return (
    <Section title="Usage">
      <dl>
        <DefinitionRow label="Times sent">{asset.usage_count}</DefinitionRow>
        <DefinitionRow label="Can be deleted">
          {asset.usage_count === 0 ? "Yes" : "No — it has been sent"}
        </DefinitionRow>
      </dl>
      <p className="mt-3 text-xs text-text-disabled">
        {asset.usage_count === 0
          ? "Nothing has used this file yet, so deleting it affects no message."
          : "This file has been sent, so it is kept: deleting it would break the record of messages already delivered. Upload a new file instead."}
      </p>
    </Section>
  );
}
