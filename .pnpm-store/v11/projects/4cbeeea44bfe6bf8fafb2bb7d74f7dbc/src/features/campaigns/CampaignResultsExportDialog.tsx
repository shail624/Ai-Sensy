import { Download, FileDown, FolderDown } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, ErrorState, Field, Modal, Select } from "@/components/ui";
import {
  apiErrorMessage,
  useCampaignResultsExport,
  useStartCampaignResultsExport,
} from "@/features/campaigns/api";
import { formatCount } from "@/features/campaigns/format";
import type {
  Campaign,
  CampaignResultsExportFormat,
  CampaignResultsExportStatus,
} from "@/features/campaigns/types";
import {
  RECIPIENT_STATUSES,
  RECIPIENT_STATUS_LABELS,
} from "@/features/campaigns/types";

interface Props {
  campaign: Campaign;
  onClose: () => void;
}

const FORMATS: { value: CampaignResultsExportFormat; label: string }[] = [
  { value: "xlsx", label: "Excel workbook" },
  { value: "csv", label: "CSV spreadsheet" },
  { value: "pdf", label: "PDF document" },
  { value: "json", label: "JSON data" },
];

/** Complete server-side campaign ledger export; never a copy of the currently visible roster page. */
export function CampaignResultsExportDialog({ campaign, onClose }: Props): JSX.Element {
  const [format, setFormat] = useState<CampaignResultsExportFormat>("xlsx");
  const [recipientStatus, setRecipientStatus] = useState<CampaignResultsExportStatus | "">("");
  const [exportId, setExportId] = useState<string | null>(null);
  const start = useStartCampaignResultsExport();
  const progress = useCampaignResultsExport(campaign.id, exportId);
  const job = progress.data;

  function generate(): void {
    start.mutate(
      {
        campaignId: campaign.id,
        body: { format, status: recipientStatus || null },
      },
      { onSuccess: (accepted) => setExportId(accepted.job.id) },
    );
  }

  return (
    <Modal title="Export campaign results" onClose={onClose} variant="sheet">
      <div className="space-y-4">
        <div className="rounded-lg border border-border bg-surface-2 p-3">
          <p className="text-sm font-semibold text-text-primary">{campaign.name}</p>
          <p className="mt-1 text-xs leading-relaxed text-text-secondary">
            The worker reads the complete persisted recipient ledger—not only the page currently
            visible. Provider IDs, message IDs, variable payloads and internal error details are
            excluded. Contact name and phone reflect their current saved values.
          </p>
        </div>

        <Field htmlFor="campaign-export-format" label="File format">
          <Select
            id="campaign-export-format"
            value={format}
            disabled={Boolean(exportId)}
            onChange={(event) => setFormat(event.target.value as CampaignResultsExportFormat)}
          >
            {FORMATS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </Select>
        </Field>

        <Field
          htmlFor="campaign-export-status"
          label="Recipient status"
          description="Optional · export every recipient or one delivery state"
        >
          <Select
            id="campaign-export-status"
            value={recipientStatus}
            disabled={Boolean(exportId)}
            onChange={(event) =>
              setRecipientStatus(event.target.value as CampaignResultsExportStatus | "")
            }
          >
            <option value="">All recipient statuses</option>
            {RECIPIENT_STATUSES.map((status) => (
              <option key={status} value={status}>{RECIPIENT_STATUS_LABELS[status]}</option>
            ))}
          </Select>
        </Field>

        {start.error ? <ErrorState message={apiErrorMessage(start.error)} /> : null}
        {progress.isError ? <ErrorState message={apiErrorMessage(progress.error)} /> : null}

        {exportId ? (
          <div className="rounded-lg border border-border bg-surface-2 p-3" role="status">
            {job?.status === "failed" ? (
              <p className="text-sm font-medium text-danger">
                Result generation failed. Start a fresh export from this campaign.
              </p>
            ) : job?.download_url ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">Campaign results ready</p>
                  <p className="text-xs text-text-secondary">
                    {formatCount(job.row_count)} recipient{job.row_count === 1 ? "" : "s"} included.
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
                  <p className="text-sm font-semibold text-text-primary">Preparing results…</p>
                  <p className="text-xs text-text-secondary">
                    You can close this window; progress is saved in Download Center.
                  </p>
                </div>
              </div>
            )}
            <Link
              to="/downloads?category=campaigns"
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
              leftIcon={<FileDown aria-hidden className="h-4 w-4" />}
              onClick={generate}
            >
              Generate results
            </Button>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}
