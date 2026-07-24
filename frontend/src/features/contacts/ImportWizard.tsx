import { CheckCircle2, FileSpreadsheet, Upload } from "lucide-react";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { Badge, Button, Modal, Spinner } from "@/components/ui";
import {
  importIsSettled,
  useContactImport,
  useInvalidateContacts,
  useStartContactImport,
} from "@/features/contacts/api";
import {
  ATTR_PREFIX,
  CONTACT_FIELDS,
  FIELD_LABELS,
  FULL_READ_LIMIT,
  MAX_UPLOAD_BYTES,
  REQUIRED_TARGET,
  SKIP,
  autoMap,
  formatBytes,
  mappingIsValid,
  readPreview,
  toRequestMapping,
  type CsvPreview,
} from "@/features/contacts/importFile";
import { useCustomAttributeDefinitions } from "@/features/customer-profile/api";
import { useUploadMedia } from "@/features/media/api";
import { apiErrorMessage } from "@/lib/api/errors";
import { useIsCompact } from "@/lib/useMediaQuery";

/** The five steps of Doc 05 B3.3, in order. */
const STEPS = ["Upload", "Map columns", "Options", "Review", "Import"] as const;
type Step = 0 | 1 | 2 | 3 | 4;

const DEDUP = [
  { value: "skip", label: "Skip duplicates", hint: "Keep the contact already on file, ignore the row." },
  { value: "merge", label: "Merge", hint: "Fill in blanks from the file, keep existing values." },
  { value: "overwrite", label: "Overwrite", hint: "The file wins for every mapped column." },
] as const;

const FIELD =
  "h-9 w-full rounded-lg border border-border bg-surface px-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

interface Props {
  onClose: () => void;
}

/**
 * Contact import (Doc 05 B3.3). Headers and the preview are read in the browser, so mapping is
 * immediate and no file reaches the server until the import actually starts; the row work itself is
 * a job, polled to a partial-success result with a downloadable error report.
 */
export function ImportWizard({ onClose }: Props): JSX.Element {
  const compact = useIsCompact();
  const definitions = useCustomAttributeDefinitions();
  const invalidateContacts = useInvalidateContacts();
  const upload = useUploadMedia();
  const start = useStartContactImport();

  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [dedup, setDedup] = useState<string>("skip");
  const [fileError, setFileError] = useState<string | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const progress = useContactImport(importId);
  const settled = importIsSettled(progress.data);
  const targets = [
    ...CONTACT_FIELDS.map((value) => ({ value, label: FIELD_LABELS[value] ?? value })),
    ...(definitions.data ?? []).map((definition) => ({
      value: `${ATTR_PREFIX}${definition.key_name}`,
      label: `${definition.label} (attribute)`,
    })),
  ];

  async function accept(candidate: File): Promise<void> {
    setFileError(null);
    if (!/\.csv$/i.test(candidate.name)) {
      setFileError("Choose a CSV file. Excel files are not supported here yet.");
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setFileError(`That file is ${formatBytes(candidate.size)}. The limit is 100 MB.`);
      return;
    }
    const complete = candidate.size <= FULL_READ_LIMIT;
    const text = await (complete ? candidate.text() : candidate.slice(0, 64 * 1024).text());
    const parsed = readPreview(text, { complete });
    if (parsed.headers.length === 0) {
      setFileError("That file has no header row.");
      return;
    }
    setFile(candidate);
    setPreview(parsed);
    setMapping(autoMap(parsed.headers, definitions.data ?? []));
    setStep(1);
  }

  function onDrop(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    const dropped = event.dataTransfer.files[0];
    if (dropped) void accept(dropped);
  }

  function onPick(event: ChangeEvent<HTMLInputElement>): void {
    const picked = event.target.files?.[0];
    if (picked) void accept(picked);
  }

  function startImport(): void {
    if (!file) return;
    setStep(4);
    upload.mutate(
      { file, mediaType: "document" },
      {
        onSuccess: (asset) =>
          start.mutate(
            {
              uploadId: asset.id,
              format: "csv",
              mapping: toRequestMapping(mapping),
              dedupStrategy: dedup,
            },
            { onSuccess: (accepted) => setImportId(accepted.job.id) },
          ),
      },
    );
  }

  /** Guard the exit once a file is loaded and the import has not been handed to the server. */
  function requestClose(): void {
    if (file && !importId && !window.confirm("Discard this import? Your column mapping will be lost."))
      return;
    if (importId) invalidateContacts();
    onClose();
  }

  const mapped = Object.values(mapping).filter((target) => target !== SKIP).length;
  const startError = upload.error ?? start.error;

  return (
    <Modal title="Import contacts" variant={compact ? "sheet" : "center"} onClose={requestClose}>
      <ol className="mb-4 flex flex-wrap items-center gap-1.5 text-xs">
        {STEPS.map((label, index) => (
          <li
            key={label}
            aria-current={index === step ? "step" : undefined}
            className={`rounded-full px-2.5 py-1 font-medium ${
              index === step
                ? "bg-accent text-accent-fg"
                : index < step
                  ? "bg-accent-soft text-accent"
                  : "bg-surface-2 text-text-disabled"
            }`}
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <div className="space-y-3">
          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            className="rounded-xl border-2 border-dashed border-border bg-surface-2 px-4 py-8 text-center"
          >
            <Upload aria-hidden className="mx-auto mb-2 h-6 w-6 text-text-disabled" />
            <p className="text-sm font-medium text-text-primary">Drop a CSV here</p>
            <p className="mb-3 text-xs text-text-secondary">Up to 100 MB, with a header row.</p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={onPick}
              className="sr-only"
              aria-label="Choose a CSV file"
            />
            <Button variant="secondary" size="sm" onClick={() => inputRef.current?.click()}>
              Choose a file
            </Button>
          </div>
          {fileError ? (
            <p role="alert" className="text-sm text-danger">
              {fileError}
            </p>
          ) : null}
          <p className="text-xs text-text-secondary">
            The first row must name the columns. One column has to hold the phone number in E.164
            form, for example <code className="text-text-primary">+14155550001</code>.
          </p>
        </div>
      )}

      {step === 1 && preview && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <FileSpreadsheet aria-hidden className="h-4 w-4" />
            <span className="truncate font-medium text-text-primary">{file?.name}</span>
            <span>· {preview.headers.length} columns</span>
          </div>

          <div className="max-h-64 overflow-y-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-2">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-[11px] uppercase tracking-wide text-text-disabled">
                    Column
                  </th>
                  <th scope="col" className="px-3 py-2 text-left text-[11px] uppercase tracking-wide text-text-disabled">
                    Imports as
                  </th>
                </tr>
              </thead>
              <tbody>
                {preview.headers.map((header, index) => (
                  <tr key={header} className="border-t border-border">
                    <td className="px-3 py-2 align-top">
                      <p className="font-medium text-text-primary">{header}</p>
                      <p className="truncate text-xs text-text-disabled">
                        {preview.rows[0]?.[index] || "—"}
                      </p>
                    </td>
                    <td className="px-3 py-2">
                      <label className="sr-only" htmlFor={`map-${index}`}>
                        Map column {header}
                      </label>
                      <select
                        id={`map-${index}`}
                        value={mapping[header] ?? SKIP}
                        onChange={(event) =>
                          setMapping((prev) => ({ ...prev, [header]: event.target.value }))
                        }
                        className={FIELD}
                      >
                        <option value={SKIP}>Do not import</option>
                        {targets.map((target) => (
                          <option key={target.value} value={target.value}>
                            {target.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!mappingIsValid(mapping) ? (
            <p role="alert" className="text-sm text-danger">
              Map one column to {FIELD_LABELS[REQUIRED_TARGET]} — an import without it is rejected.
            </p>
          ) : null}
        </div>
      )}

      {step === 2 && (
        <fieldset className="space-y-2">
          <legend className="mb-1 text-xs font-semibold text-text-secondary">
            When a contact already exists
          </legend>
          {DEDUP.map((option) => (
            <label
              key={option.value}
              className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-2.5 ${
                dedup === option.value ? "border-accent bg-accent-soft" : "border-border"
              }`}
            >
              <input
                type="radio"
                name="dedup"
                value={option.value}
                checked={dedup === option.value}
                onChange={() => setDedup(option.value)}
                className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
              />
              <span>
                <span className="block text-sm font-medium text-text-primary">{option.label}</span>
                <span className="block text-xs text-text-secondary">{option.hint}</span>
              </span>
            </label>
          ))}
          <p className="rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-xs text-text-secondary">
            Opt-in is never assumed. A contact counts as opted in only where the file says so through
            a mapped opt-in column, or where they message you first.
          </p>
        </fieldset>
      )}

      {step === 3 && (
        <dl className="space-y-2 text-sm">
          <Row label="File" value={`${file?.name ?? ""} · ${formatBytes(file?.size ?? 0)}`} />
          <Row
            label="Rows"
            value={
              preview?.rowCount != null
                ? preview.rowCount.toLocaleString()
                : "counted by the server while it reads the file"
            }
          />
          <Row label="Columns imported" value={`${mapped} of ${preview?.headers.length ?? 0}`} />
          <Row label="Duplicates" value={DEDUP.find((item) => item.value === dedup)?.label ?? dedup} />
          <p className="pt-1 text-xs text-text-secondary">
            The import runs in the background. You can close this dialog once it has started.
          </p>
        </dl>
      )}

      {step === 4 && (
        <ImportResult
          uploading={upload.isPending}
          starting={start.isPending}
          error={startError ? apiErrorMessage(startError) : null}
          progress={progress.data}
          settled={settled}
        />
      )}

      <div className="mt-5 flex gap-2 border-t border-border pt-4">
        {step === 4 ? (
          <Button block onClick={requestClose}>
            {settled ? "Done" : "Close and keep importing"}
          </Button>
        ) : (
          <>
            <Button
              variant="secondary"
              block
              onClick={() => (step === 0 ? requestClose() : setStep((step - 1) as Step))}
            >
              {step === 0 ? "Cancel" : "Back"}
            </Button>
            <Button
              block
              disabled={
                (step === 0 && !file) || (step === 1 && !mappingIsValid(mapping)) || definitions.isLoading
              }
              onClick={() => (step === 3 ? startImport() : setStep((step + 1) as Step))}
            >
              {step === 3 ? "Start import" : "Continue"}
            </Button>
          </>
        )}
      </div>
    </Modal>
  );
}

function Row({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="flex justify-between gap-4 border-b border-border pb-2 last:border-0">
      <dt className="text-text-secondary">{label}</dt>
      <dd className="text-right font-medium text-text-primary">{value}</dd>
    </div>
  );
}

function ImportResult({
  uploading,
  starting,
  error,
  progress,
  settled,
}: {
  uploading: boolean;
  starting: boolean;
  error: string | null;
  progress: { total_rows: number | null; processed_rows: number; success_rows: number; error_rows: number; error_report_url: string | null; status: string } | undefined;
  settled: boolean;
}): JSX.Element {
  if (error) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  if (uploading || starting || !progress) {
    return (
      <div className="flex items-center gap-3 py-6">
        <Spinner />
        <p className="text-sm text-text-secondary">
          {uploading ? "Uploading your file…" : "Starting the import…"}
        </p>
      </div>
    );
  }

  const total = progress.total_rows;
  const pct = total ? Math.min(100, Math.round((progress.processed_rows / total) * 100)) : null;

  if (!settled) {
    return (
      <div className="space-y-3 py-2">
        <div className="flex items-center gap-3">
          <Spinner />
          <p className="text-sm text-text-secondary" role="status">
            {progress.processed_rows.toLocaleString()}
            {total ? ` of ${total.toLocaleString()}` : ""} rows processed
          </p>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: pct != null ? `${pct}%` : "35%" }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {progress.error_rows > 0 ? (
          <Badge tone="warning" dot>
            Finished with errors
          </Badge>
        ) : (
          <Badge tone="success" dot>
            <CheckCircle2 aria-hidden className="h-3.5 w-3.5" /> Imported
          </Badge>
        )}
        <span className="text-sm text-text-secondary">
          {progress.success_rows.toLocaleString()} contacts
          {progress.error_rows > 0 ? ` · ${progress.error_rows.toLocaleString()} rows failed` : ""}
        </span>
      </div>
      {progress.error_report_url ? (
        <a
          href={progress.error_report_url}
          download
          className="inline-flex h-9 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-text-primary hover:bg-hover"
        >
          Download error report
        </a>
      ) : null}
    </div>
  );
}
