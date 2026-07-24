import { useState } from "react";

import { Badge, Button, Modal, Spinner } from "@/components/ui";
import {
  isSettled,
  useBulkDeleteContacts,
  useBulkEditContacts,
  useBulkProgress,
  useContactExport,
  useInvalidateContacts,
  useStartContactExport,
} from "@/features/contacts/api";
import type { BulkProgress, SegmentRule } from "@/features/contacts/types";
import { useCustomAttributeDefinitions, useTags } from "@/features/customer-profile/api";
import { apiErrorMessage } from "@/lib/api/errors";
import { useIsCompact } from "@/lib/useMediaQuery";

/** Every bulk operation the API exposes for a contact selection. */
export type BulkMode = "add_tags" | "remove_tags" | "set_attributes" | "delete" | "export";

const TITLES: Record<BulkMode, string> = {
  add_tags: "Add tags",
  remove_tags: "Remove tags",
  set_attributes: "Set an attribute",
  delete: "Delete contacts",
  export: "Export contacts",
};

const EXPORT_FORMATS = ["csv", "xlsx", "json"] as const;

const FIELD =
  "h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50";

interface Props {
  mode: BulkMode;
  /** The selected contact ids. Export ignores them — it addresses by rule (Doc 04 §30). */
  ids: string[];
  /** The active filters, so an export covers exactly the view the user is looking at. */
  rules: SegmentRule[];
  onClose: () => void;
  /** Called once a job has finished and the caller should drop its selection. */
  onCompleted: () => void;
}

/**
 * One dialog for every bulk operation (Doc 05 B3.1 "Bulk Actions", DS-14). The shape is always the
 * same: choose, confirm, then watch the job. Nothing mutates on the request path — the API returns
 * `202` and this polls the §29 partial-success envelope until it settles.
 */
export function BulkActionDialog({ mode, ids, rules, onClose, onCompleted }: Props): JSX.Element {
  const compact = useIsCompact();
  const tags = useTags();
  const definitions = useCustomAttributeDefinitions();
  const invalidateContacts = useInvalidateContacts();

  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [attributeKey, setAttributeKey] = useState("");
  const [attributeValue, setAttributeValue] = useState("");
  const [format, setFormat] = useState<string>("csv");
  const [bulkId, setBulkId] = useState<string | null>(null);
  const [exportId, setExportId] = useState<string | null>(null);

  const edit = useBulkEditContacts();
  const remove = useBulkDeleteContacts();
  const startExport = useStartContactExport();
  const progress = useBulkProgress(bulkId);
  const exportJob = useContactExport(exportId);

  const definition = (definitions.data ?? []).find((item) => item.key_name === attributeKey);
  const pending = edit.isPending || remove.isPending || startExport.isPending;
  const running = Boolean(bulkId) && !isSettled(progress.data);
  const startError = edit.error ?? remove.error ?? startExport.error;

  function confirm(): void {
    if (mode === "delete") {
      remove.mutate(ids, { onSuccess: (accepted) => setBulkId(accepted.job.id) });
      return;
    }
    if (mode === "export") {
      startExport.mutate({ format, rules }, { onSuccess: (accepted) => setExportId(accepted.job.id) });
      return;
    }
    const payload =
      mode === "set_attributes"
        ? { attributes: { [attributeKey]: attributeValue } }
        : { tags: selectedTags };
    edit.mutate({ ids, action: mode, payload }, { onSuccess: (accepted) => setBulkId(accepted.job.id) });
  }

  /** The confirm button stays disabled until the operation has everything it needs. */
  const ready =
    mode === "delete" ||
    mode === "export" ||
    (mode === "set_attributes" ? Boolean(attributeKey && attributeValue) : selectedTags.length > 0);

  function finish(): void {
    invalidateContacts();
    onCompleted();
    onClose();
  }

  return (
    <Modal title={TITLES[mode]} variant={compact ? "sheet" : "center"} onClose={onClose}>
      {bulkId ? (
        <BulkResult progress={progress.data} onDone={finish} />
      ) : exportId ? (
        <ExportResult
          status={exportJob.data?.status}
          rowCount={exportJob.data?.row_count ?? null}
          downloadUrl={exportJob.data?.download_url ?? null}
          onDone={finish}
        />
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            {mode === "export" ? (
              <>
                Exports cover <strong className="text-text-primary">the whole filtered view</strong>,
                not just the rows you selected.
              </>
            ) : (
              <>
                This applies to{" "}
                <strong className="text-text-primary">
                  {ids.length.toLocaleString()} selected contact{ids.length === 1 ? "" : "s"}
                </strong>
                .
              </>
            )}
          </p>

          {(mode === "add_tags" || mode === "remove_tags") && (
            <fieldset className="space-y-1.5">
              <legend className="mb-1 text-xs font-semibold text-text-secondary">Tags</legend>
              {tags.isLoading ? (
                <Spinner />
              ) : (tags.data ?? []).length === 0 ? (
                <p className="text-sm text-text-disabled">No tags exist yet.</p>
              ) : (
                <div className="max-h-52 space-y-1 overflow-y-auto pr-1">
                  {(tags.data ?? []).map((tag) => (
                    <label
                      key={tag.id}
                      className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-hover"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTags.includes(tag.id)}
                        onChange={() =>
                          setSelectedTags((prev) =>
                            prev.includes(tag.id)
                              ? prev.filter((id) => id !== tag.id)
                              : [...prev, tag.id],
                          )
                        }
                        className="h-4 w-4 accent-[var(--color-accent)]"
                      />
                      <span
                        aria-hidden
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: tag.color ?? "var(--color-text-disabled)" }}
                      />
                      <span className="text-sm text-text-primary">{tag.name}</span>
                    </label>
                  ))}
                </div>
              )}
            </fieldset>
          )}

          {mode === "set_attributes" && (
            <div className="space-y-3">
              <div>
                <label htmlFor="bulk-attr" className="mb-1 block text-xs font-semibold text-text-secondary">
                  Attribute
                </label>
                <select
                  id="bulk-attr"
                  value={attributeKey}
                  onChange={(event) => {
                    setAttributeKey(event.target.value);
                    setAttributeValue("");
                  }}
                  className={FIELD}
                >
                  <option value="">Choose an attribute…</option>
                  {(definitions.data ?? []).map((item) => (
                    <option key={item.id} value={item.key_name}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="bulk-attr-value" className="mb-1 block text-xs font-semibold text-text-secondary">
                  Value
                </label>
                {definition?.data_type === "enum" ? (
                  <select
                    id="bulk-attr-value"
                    value={attributeValue}
                    onChange={(event) => setAttributeValue(event.target.value)}
                    disabled={!attributeKey}
                    className={FIELD}
                  >
                    <option value="">Choose a value…</option>
                    {(definition.enum_values ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id="bulk-attr-value"
                    value={attributeValue}
                    onChange={(event) => setAttributeValue(event.target.value)}
                    disabled={!attributeKey}
                    className={FIELD}
                  />
                )}
              </div>
            </div>
          )}

          {mode === "export" && (
            <div>
              <label htmlFor="bulk-format" className="mb-1 block text-xs font-semibold text-text-secondary">
                Format
              </label>
              <select
                id="bulk-format"
                value={format}
                onChange={(event) => setFormat(event.target.value)}
                className={FIELD}
              >
                {EXPORT_FORMATS.map((value) => (
                  <option key={value} value={value}>
                    {value.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          )}

          {mode === "delete" && (
            <p className="rounded-lg border border-danger bg-danger-soft px-3 py-2.5 text-sm text-danger">
              Deleted contacts stop receiving messages and leave every segment. This cannot be undone
              from here.
            </p>
          )}

          {startError ? (
            <p role="alert" className="text-sm text-danger">
              {apiErrorMessage(startError)}
            </p>
          ) : null}

          <div className="flex gap-2 border-t border-border pt-4">
            <Button variant="secondary" block onClick={onClose}>
              Cancel
            </Button>
            <Button
              block
              variant={mode === "delete" ? "danger" : "primary"}
              loading={pending}
              disabled={!ready || pending}
              onClick={confirm}
            >
              {mode === "delete" ? "Delete" : mode === "export" ? "Export" : "Apply"}
            </Button>
          </div>
        </div>
      )}
      {running ? (
        <span className="sr-only" role="status">
          Working…
        </span>
      ) : null}
    </Modal>
  );
}

/** The §29 partial-success envelope: counts first, then the per-item errors behind them. */
function BulkResult({
  progress,
  onDone,
}: {
  progress: BulkProgress | undefined;
  onDone: () => void;
}): JSX.Element {
  if (!progress || !isSettled(progress)) {
    return (
      <div className="flex items-center gap-3 py-6">
        <Spinner />
        <div>
          <p className="text-sm font-medium text-text-primary">Working through your selection…</p>
          <p className="text-xs text-text-secondary">
            {progress ? `${progress.summary.processed.toLocaleString()} processed` : "Starting…"}
          </p>
        </div>
      </div>
    );
  }

  const { summary } = progress;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={summary.failed > 0 ? "warning" : "success"} dot>
          {summary.failed > 0 ? "Finished with errors" : "Finished"}
        </Badge>
        <span className="text-sm text-text-secondary">
          {summary.succeeded.toLocaleString()} updated
          {summary.skipped > 0 ? ` · ${summary.skipped.toLocaleString()} skipped` : ""}
          {summary.failed > 0 ? ` · ${summary.failed.toLocaleString()} failed` : ""}
        </span>
      </div>

      {progress.errors.length > 0 ? (
        <ul className="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-border bg-surface-2 p-2 text-xs">
          {progress.errors.map((error, index) => (
            <li key={`${error.id ?? "row"}-${index}`} className="text-text-secondary">
              <span className="font-medium text-danger">{error.code}</span> — {error.message}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex gap-2 border-t border-border pt-4">
        {progress.error_report_url ? (
          <a
            href={progress.error_report_url}
            download
            className="inline-flex h-9 flex-1 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-text-primary hover:bg-hover"
          >
            Download error report
          </a>
        ) : null}
        <Button block onClick={onDone}>
          Done
        </Button>
      </div>
    </div>
  );
}

function ExportResult({
  status,
  rowCount,
  downloadUrl,
  onDone,
}: {
  status: string | undefined;
  rowCount: number | null;
  downloadUrl: string | null;
  onDone: () => void;
}): JSX.Element {
  if (status === "failed") {
    return (
      <div className="space-y-4">
        <p role="alert" className="text-sm text-danger">
          The export failed. Try again, or narrow the filters first.
        </p>
        <Button block onClick={onDone}>
          Close
        </Button>
      </div>
    );
  }

  if (!downloadUrl) {
    return (
      <div className="flex items-center gap-3 py-6">
        <Spinner />
        <p className="text-sm text-text-secondary">Preparing your export…</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        {rowCount != null ? `${rowCount.toLocaleString()} contacts ready.` : "Your export is ready."}{" "}
        The link expires — download it now.
      </p>
      <div className="flex gap-2 border-t border-border pt-4">
        <a
          href={downloadUrl}
          download
          className="inline-flex h-9 flex-1 items-center justify-center rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:bg-accent-strong"
        >
          Download
        </a>
        <Button variant="secondary" block onClick={onDone}>
          Close
        </Button>
      </div>
    </div>
  );
}
