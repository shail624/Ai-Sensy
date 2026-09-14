import { Check, FileImage, Search, UploadCloud } from "lucide-react";
import { useMemo, useState } from "react";

import { Button, EmptyState, Spinner } from "@/components/ui";
import { apiErrorMessage, useMediaList, useUploadMedia } from "@/features/media/api";
import { mediaTypeForMime, validateUpload } from "@/features/media/selectors";
import type { MediaAsset, MediaType } from "@/features/media/types";
import { useHasPermission } from "@/lib/auth";
import { formatBytes } from "@/lib/format";

interface Props {
  value: MediaAsset | null;
  onChange: (asset: MediaAsset) => void;
}

export function DocumentAssetPicker({ value, onChange }: Props): JSX.Element {
  const [query, setQuery] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const media = useMediaList();
  const upload = useUploadMedia();
  const canUpload = useHasPermission("media:write");
  const candidates = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (media.data?.data ?? [])
      .filter((asset) => asset.media_type === "document" || asset.media_type === "image")
      .filter((asset) => !needle || (asset.file_name ?? asset.mime_type).toLowerCase().includes(needle))
      .slice(0, 12);
  }, [media.data, query]);

  const guessed = file ? mediaTypeForMime(file.type) : null;
  const uploadType: MediaType = guessed === "image" ? "image" : "document";
  const problem = file ? validateUpload(file, uploadType) : null;

  function uploadFile(): void {
    if (!file || problem) return;
    upload.mutate(
      { file, mediaType: uploadType },
      {
        onSuccess: (asset) => {
          onChange(asset);
          setFile(null);
        },
      },
    );
  }

  return (
    <div className="space-y-3">
      {canUpload ? (
        <div className="rounded-xl border border-dashed border-accent/40 bg-accent-soft/40 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface text-accent shadow-sm">
              <UploadCloud aria-hidden className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <label htmlFor="document-file" className="block text-sm font-semibold text-text-primary">
                Upload a new file
              </label>
              <p className="mt-0.5 text-xs text-text-secondary">
                PDF, office document, or image. Files are scanned and deduplicated before linking.
              </p>
              <input
                id="document-file"
                type="file"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="mt-2 block w-full text-xs text-text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-surface file:px-3 file:py-2 file:text-xs file:font-semibold file:text-text-primary"
              />
            </div>
            <Button size="sm" onClick={uploadFile} disabled={!file || Boolean(problem)} loading={upload.isPending}>
              Upload & select
            </Button>
          </div>
          {file ? (
            <p className={`mt-2 text-xs ${problem ? "text-danger" : "text-text-secondary"}`}>
              {problem ? problem.message : `${file.name} · ${formatBytes(file.size)}`}
            </p>
          ) : null}
          {upload.isError ? <p className="mt-2 text-xs text-danger">{apiErrorMessage(upload.error)}</p> : null}
        </div>
      ) : null}

      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3">
        <Search aria-hidden className="h-4 w-4 text-text-disabled" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search recent secure files"
          className="h-10 w-full bg-transparent text-sm text-text-primary outline-none placeholder:text-text-disabled"
        />
      </div>

      {media.isLoading ? <Spinner label="Loading secure files…" /> : null}
      {!media.isLoading && candidates.length === 0 ? (
        <EmptyState
          compact
          title="No eligible files"
          description={canUpload ? "Upload the first file above." : "A manager can upload a file to the secure media library."}
        />
      ) : null}
      {candidates.length > 0 ? (
        <div className="grid max-h-60 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          {candidates.map((asset) => {
            const selected = value?.id === asset.id;
            return (
              <button
                key={asset.id}
                type="button"
                onClick={() => onChange(asset)}
                aria-pressed={selected}
                className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${selected ? "border-accent bg-accent-soft shadow-sm" : "border-border bg-surface hover:border-accent/40 hover:bg-hover"}`}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-accent">
                  <FileImage aria-hidden className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-text-primary">
                    {asset.file_name ?? "Untitled file"}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-text-secondary">
                    {asset.mime_type} · {formatBytes(asset.byte_size)}
                  </span>
                </span>
                {selected ? <Check aria-hidden className="h-4 w-4 shrink-0 text-accent" /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
      {value ? (
        <p className="flex items-center gap-1.5 text-xs font-medium text-success">
          <Check aria-hidden className="h-3.5 w-3.5" /> {value.file_name ?? "File"} selected
        </p>
      ) : null}
    </div>
  );
}
