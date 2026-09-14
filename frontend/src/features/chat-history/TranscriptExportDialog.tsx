import { Download, FileDown, FolderDown } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, ErrorState, Field, Input, Modal, Select } from "@/components/ui";
import {
  apiErrorMessage,
  type TranscriptFormat,
  useStartTranscriptExport,
  useTranscriptExport,
} from "@/features/chat-history/api";

interface Props {
  conversationId: string;
  contactName: string;
  onClose: () => void;
}

const FORMATS: { value: TranscriptFormat; label: string }[] = [
  { value: "pdf", label: "PDF document" },
  { value: "csv", label: "CSV spreadsheet" },
  { value: "xlsx", label: "Excel workbook" },
  { value: "json", label: "JSON data" },
];

function localDateIso(value: string, nextDay = false): string | null {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day + (nextDay ? 1 : 0)).toISOString();
}

/** A selected-thread export; it never downloads browser-loaded pages or silently drops old rows. */
export function TranscriptExportDialog({
  conversationId,
  contactName,
  onClose,
}: Props): JSX.Element {
  const [format, setFormat] = useState<TranscriptFormat>("pdf");
  const [fromDate, setFromDate] = useState("");
  const [throughDate, setThroughDate] = useState("");
  const [exportId, setExportId] = useState<string | null>(null);
  const start = useStartTranscriptExport();
  const progress = useTranscriptExport(exportId);
  const invalidRange = Boolean(fromDate && throughDate && fromDate > throughDate);
  const job = progress.data;

  function generate(): void {
    if (invalidRange) return;
    start.mutate(
      {
        conversation_id: conversationId,
        format,
        from: localDateIso(fromDate),
        to: localDateIso(throughDate, true),
      },
      { onSuccess: (accepted) => setExportId(accepted.job.id) },
    );
  }

  return (
    <Modal title="Export chat transcript" onClose={onClose} variant="sheet">
      <div className="space-y-4">
        <div className="rounded-lg border border-border bg-surface-2 p-3">
          <p className="text-sm font-semibold text-text-primary">{contactName}</p>
          <p className="mt-1 text-xs leading-relaxed text-text-secondary">
            The worker reads the complete persisted thread, not only messages currently loaded on
            this screen. Provider IDs, private media links and storage references are excluded.
          </p>
        </div>

        <Field htmlFor="transcript-format" label="File format">
          <Select
            id="transcript-format"
            value={format}
            disabled={Boolean(exportId)}
            onChange={(event) => setFormat(event.target.value as TranscriptFormat)}
          >
            {FORMATS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </Select>
        </Field>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field htmlFor="transcript-from" label="From date" description="Optional · device time zone">
            <Input
              id="transcript-from"
              type="date"
              value={fromDate}
              disabled={Boolean(exportId)}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </Field>
          <Field htmlFor="transcript-through" label="Through date" description="Optional · entire day">
            <Input
              id="transcript-through"
              type="date"
              value={throughDate}
              disabled={Boolean(exportId)}
              onChange={(event) => setThroughDate(event.target.value)}
            />
          </Field>
        </div>
        {invalidRange ? (
          <p className="text-xs font-medium text-danger" role="alert">
            From date must be on or before the through date.
          </p>
        ) : null}

        {start.error ? <ErrorState message={apiErrorMessage(start.error)} /> : null}
        {progress.isError ? <ErrorState message={apiErrorMessage(progress.error)} /> : null}

        {exportId ? (
          <div className="rounded-lg border border-border bg-surface-2 p-3" role="status">
            {job?.status === "failed" ? (
              <p className="text-sm font-medium text-danger">
                Transcript generation failed. Start a fresh export from this conversation.
              </p>
            ) : job?.download_url ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">Transcript ready</p>
                  <p className="text-xs text-text-secondary">
                    {job.row_count ?? 0} message{job.row_count === 1 ? "" : "s"} included.
                  </p>
                </div>
                <a
                  href={job.download_url}
                  download
                  className="inline-flex h-9 items-center gap-2 rounded-control bg-accent px-3 text-sm font-semibold text-accent-fg"
                >
                  <Download aria-hidden className="h-4 w-4" /> Download file
                </a>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <FileDown aria-hidden className="h-5 w-5 text-accent" />
                <div>
                  <p className="text-sm font-semibold text-text-primary">Preparing transcript…</p>
                  <p className="text-xs text-text-secondary">
                    You can close this window; progress is saved in Download Center.
                  </p>
                </div>
              </div>
            )}
            <Link
              to="/downloads?category=chat_history"
              className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-accent hover:underline"
            >
              <FolderDown aria-hidden className="h-4 w-4" /> Open Download Center
            </Link>
          </div>
        ) : null}

        <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-3">
          <Button variant="secondary" onClick={onClose}>Close</Button>
          {!exportId ? (
            <Button
              loading={start.isPending}
              disabled={invalidRange}
              leftIcon={<FileDown aria-hidden className="h-4 w-4" />}
              onClick={generate}
            >
              Generate transcript
            </Button>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}
