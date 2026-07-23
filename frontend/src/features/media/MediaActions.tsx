import { useState } from "react";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import {
  apiErrorMessage,
  useDeleteMedia,
  useHasPermission,
  useMediaContent,
} from "@/features/media/api";
import { MediaUploadDialog } from "@/features/media/MediaUploadDialog";
import { displayName } from "@/features/media/selectors";
import type { MediaAsset } from "@/features/media/types";
import { isDeletable } from "@/features/media/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  asset: MediaAsset;
  /** After a delete the detail page must leave; the list just refreshes in place. */
  onDeleted?: () => void;
  /** Download and replace need room; the compact list rows leave them to the detail page. */
  compact?: boolean;
}

/**
 * The media action set (Doc 04 §16), gated twice over.
 *
 * **By permission**, using the codes the API enforces: `media:write` to upload, replace and delete;
 * everything else needs only `media:read`. **By state**, using `usage_count` — an asset that has
 * been sent in a message cannot be deleted, and the server answers 409, so Delete is not offered
 * and the reason is shown in its place.
 *
 * One implementation, used by the list rows and the detail page.
 */
export function MediaActions({ asset, onDeleted, compact = false }: Props): JSX.Element {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [replacing, setReplacing] = useState(false);
  const [copied, setCopied] = useState(false);

  const canWrite = useHasPermission("media:write");
  const remove = useDeleteMedia();

  // The signed URL is only issued when a download is actually offered — it expires, and minting one
  // per row for a link nobody clicks would be a request per asset for nothing.
  const content = useMediaContent(asset.id, !compact);

  const deletable = isDeletable(asset);

  async function copyId(): Promise<void> {
    try {
      await navigator.clipboard?.writeText(asset.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be refused (insecure context, denied permission). The id is on screen
      // and selectable either way, so this fails quietly rather than raising an alarm.
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        <button type="button" className={ACTION_CLASS} onClick={() => void copyId()}>
          {copied ? "Copied" : "Copy ID"}
        </button>

        {!compact ? (
          <a
            href={content.data?.url ?? "#"}
            download={displayName(asset)}
            aria-disabled={!content.data}
            className={`${ACTION_CLASS} ${content.data ? "" : "pointer-events-none opacity-50"}`}
          >
            Download
          </a>
        ) : null}

        {canWrite && !compact ? (
          <button type="button" className={ACTION_CLASS} onClick={() => setReplacing(true)}>
            Replace
          </button>
        ) : null}

        {canWrite && deletable ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={remove.isPending}
            onClick={() => setConfirmingDelete(true)}
          >
            Delete
          </button>
        ) : null}
      </div>

      {canWrite && !deletable ? (
        <p className="text-xs text-text-disabled">In use — cannot be deleted</p>
      ) : null}

      {remove.error && !confirmingDelete ? (
        <p className="text-xs text-danger">{apiErrorMessage(remove.error)}</p>
      ) : null}

      {confirmingDelete ? (
        <ConfirmDialog
          title="Delete this file?"
          body={`"${displayName(asset)}" is removed from the library and from storage. Nothing has used it, so no message is affected.`}
          confirmLabel="Delete file"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setConfirmingDelete(false)}
          onConfirm={() =>
            remove.mutate(asset.id, {
              onSuccess: () => {
                setConfirmingDelete(false);
                onDeleted?.();
              },
            })
          }
        />
      ) : null}

      {replacing ? (
        <MediaUploadDialog replacing={asset} onClose={() => setReplacing(false)} />
      ) : null}
    </div>
  );
}
