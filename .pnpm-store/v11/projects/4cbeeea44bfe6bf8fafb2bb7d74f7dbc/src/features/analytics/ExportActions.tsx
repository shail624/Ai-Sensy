import { useState } from "react";

import { ErrorState } from "@/components/ui";
import { apiErrorMessage, useReportExport, useStartReportExport } from "@/features/analytics/api";
import type {
  AnalyticsFilterState,
  ExportFormat,
  ReportName,
} from "@/features/analytics/types";
import { EXPORT_FORMATS, REPORTS } from "@/features/analytics/types";
import { useHasPermission } from "@/lib/auth";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

/**
 * Report export (Doc 15 §19). Always async: the request returns `202` with a job, and this polls
 * the same progress envelope contact exports use until a signed download link appears. Hidden
 * entirely without `analytics:export`, which is the permission the API enforces.
 */
export function ExportActions({ filters }: { filters: AnalyticsFilterState }): JSX.Element | null {
  const canExport = useHasPermission("analytics:export");
  const [report, setReport] = useState<ReportName>("messages");
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [exportId, setExportId] = useState<string | null>(null);

  const start = useStartReportExport();
  const progress = useReportExport(exportId);

  if (!canExport) return null;

  const job = progress.data;

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="flex flex-col gap-1">
        <label htmlFor="export-report" className="text-xs font-medium text-text-secondary">
          Report
        </label>
        <select
          id="export-report"
          value={report}
          onChange={(event) => setReport(event.target.value as ReportName)}
          className={FIELD_CLASS}
        >
          {REPORTS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="export-format" className="text-xs font-medium text-text-secondary">
          Format
        </label>
        <select
          id="export-format"
          value={format}
          onChange={(event) => setFormat(event.target.value as ExportFormat)}
          className={FIELD_CLASS}
        >
          {EXPORT_FORMATS.map((option) => (
            <option key={option} value={option}>
              {option.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        disabled={start.isPending}
        onClick={() =>
          start.mutate(
            { report, format, filters },
            { onSuccess: (accepted) => setExportId(accepted.job.id) },
          )
        }
        className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
      >
        {start.isPending ? "Starting…" : "Export"}
      </button>

      {job ? (
        job.download_url ? (
          <a
            href={job.download_url}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg"
            download
          >
            Download ({job.row_count ?? 0} rows)
          </a>
        ) : job.status === "failed" ? (
          <span className="text-xs text-danger">Export failed</span>
        ) : (
          <span className="text-xs text-text-secondary" role="status">
            Preparing your export…
          </span>
        )
      ) : null}

      {start.error ? <ErrorState message={apiErrorMessage(start.error)} /> : null}
    </div>
  );
}
