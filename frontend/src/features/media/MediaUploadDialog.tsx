import { useState } from "react";

import { Modal } from "@/components/ui";
import {
  apiErrorMessage,
  useReplaceMedia,
  useUploadMedia,
  type ReplaceResult,
} from "@/features/media/api";
import { formatLimit, mediaTypeForMime, validateUpload } from "@/features/media/selectors";
import type { MediaAsset, MediaType } from "@/features/media/types";
import { acceptFor, MEDIA_RULES, MEDIA_TYPE_LABELS, MEDIA_TYPES } from "@/features/media/types";
import { formatBytes } from "@/lib/format";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

interface Props {
  /** Present → replace that asset's content; absent → add a new asset. */
  replacing?: MediaAsset;
  onClose: () => void;
  onUploaded?: (asset: MediaAsset) => void;
}

/**
 * Upload a file, or replace an existing asset's content.
 *
 * Validation mirrors `storage/validation.py` and runs at the file picker, so an over-size or
 * disallowed file is refused before a byte crosses the wire — the server re-checks and its
 * 413/415/422 is what decides.
 *
 * Two behaviours are stated rather than hidden. Uploads are **deduplicated by content**: identical
 * bytes return the asset that already holds them, which is reported instead of implying a second
 * copy was made. And a **replace** is composed from upload + delete, so when the old asset is in
 * use the server refuses to remove it and the dialog says the old one was kept.
 */
export function MediaUploadDialog({ replacing, onClose, onUploaded }: Props): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [mediaType, setMediaType] = useState<MediaType | "">(
    (replacing?.media_type as MediaType) ?? "",
  );
  const [showProblem, setShowProblem] = useState(false);
  const [outcome, setOutcome] = useState<ReplaceResult | MediaAsset | null>(null);

  const upload = useUploadMedia();
  const replace = useReplaceMedia();
  const pending = upload.isPending || replace.isPending;
  const error = upload.error ?? replace.error;

  const problem = validateUpload(file, mediaType);
  const rule = mediaType ? MEDIA_RULES[mediaType] : null;

  function choose(next: File | null): void {
    setFile(next);
    setShowProblem(false);
    // Preselect the type from the file itself, so the common case is one action instead of two.
    // Never on a replace: the asset's kind is fixed, and changing it would describe a different one.
    if (next && !replacing) {
      const guessed = mediaTypeForMime(next.type);
      if (guessed) setMediaType(guessed);
    }
  }

  function submit(): void {
    setShowProblem(true);
    if (problem || !file || !mediaType) return;

    if (replacing) {
      replace.mutate(
        { previousId: replacing.id, file, mediaType },
        { onSuccess: (result) => setOutcome(result) },
      );
      return;
    }
    upload.mutate({ file, mediaType }, { onSuccess: (asset) => setOutcome(asset) });
  }

  // --- Outcome ---------------------------------------------------------------------------------
  if (outcome) {
    const result = "asset" in outcome ? outcome : null;
    const asset = result ? result.asset : (outcome as MediaAsset);
    return (
      <Modal title={replacing ? "Replaced" : "Uploaded"} onClose={onClose}>
        <div className="space-y-3 text-sm">
          {result?.deduped ? (
            <p className="text-text-primary">
              Those bytes are already in the library, so nothing changed — this is the same asset.
              The library stores each distinct file once.
            </p>
          ) : result && !result.replaced ? (
            <p className="text-warning">
              The new file was uploaded, but the previous asset has been used in a message and
              cannot be deleted. Both remain in the library.
            </p>
          ) : result ? (
            <p className="text-text-primary">
              The new file is uploaded and the previous asset has been removed.
            </p>
          ) : (
            <p className="text-text-primary">The file is in the library.</p>
          )}

          <dl className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
            <div className="flex justify-between gap-2 py-0.5">
              <dt className="text-text-secondary">Media ID</dt>
              <dd className="font-mono text-text-primary">{asset.id}</dd>
            </div>
            <div className="flex justify-between gap-2 py-0.5">
              <dt className="text-text-secondary">Size</dt>
              <dd className="text-text-primary">{formatBytes(asset.byte_size)}</dd>
            </div>
          </dl>

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover">
              Close
            </button>
            {onUploaded ? (
              <button
                type="button"
                onClick={() => onUploaded(asset)}
                className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg"
              >
                Open asset
              </button>
            ) : null}
          </div>
        </div>
      </Modal>
    );
  }

  // --- Form ------------------------------------------------------------------------------------
  return (
    <Modal
      title={replacing ? `Replace "${replacing.file_name ?? "asset"}"` : "Upload media"}
      onClose={onClose}
    >
      <div className="space-y-3">
        <div>
          <label htmlFor="media-type" className={LABEL_CLASS}>
            Media type
          </label>
          <select
            id="media-type"
            value={mediaType}
            disabled={Boolean(replacing)}
            onChange={(event) => setMediaType(event.target.value as MediaType | "")}
            className={`${FIELD_CLASS} disabled:opacity-60`}
          >
            <option value="">Choose…</option>
            {MEDIA_TYPES.map((type) => (
              <option key={type} value={type}>
                {MEDIA_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
          {replacing ? (
            <p className="mt-1 text-xs text-text-disabled">
              A replacement keeps the same kind of media.
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="media-file" className={LABEL_CLASS}>
            File
          </label>
          <input
            id="media-file"
            type="file"
            accept={mediaType ? acceptFor(mediaType) : undefined}
            onChange={(event) => choose(event.target.files?.[0] ?? null)}
            className={FIELD_CLASS}
          />
          {rule ? (
            <p className="mt-1 text-xs text-text-disabled">
              Up to {formatLimit(rule.maxBytes)} · {rule.mimeTypes.join(", ")}
            </p>
          ) : null}
          {file ? (
            <p className="mt-1 text-xs text-text-secondary">
              {file.name} · {formatBytes(file.size)}
              {file.type ? ` · ${file.type}` : ""}
            </p>
          ) : null}
        </div>

        {showProblem && problem ? <p className="text-sm text-danger">{problem.message}</p> : null}
        {error ? <p className="text-sm text-danger">{apiErrorMessage(error)}</p> : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {pending ? "Uploading…" : replacing ? "Replace file" : "Upload"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
