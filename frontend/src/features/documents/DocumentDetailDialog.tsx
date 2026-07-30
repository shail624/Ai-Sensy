import {
  Archive,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileClock,
  FileText,
  History,
  Plus,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { useState } from "react";

import { Badge, Button, ErrorState, Modal, Spinner } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import {
  apiErrorMessage,
  useArchiveDocument,
  useDocumentContent,
  useDocumentHistory,
  useExpireDocument,
  useVerifyDocument,
} from "@/features/documents/api";
import {
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
  type CustomerDocument,
  type DocumentStatus,
} from "@/features/documents/types";
import { useHasPermission } from "@/lib/auth";
import { formatBytes } from "@/lib/format";

const STATUS_TONE: Record<DocumentStatus, BadgeTone> = {
  submitted: "warning",
  verified: "success",
  rejected: "danger",
  expired: "neutral",
  archived: "neutral",
};

interface Props {
  document: CustomerDocument;
  onClose: () => void;
  onAddVersion: () => void;
}

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function DocumentDetailDialog({ document, onClose, onAddVersion }: Props): JSX.Element {
  const [decision, setDecision] = useState<"reject" | "archive" | null>(null);
  const [reason, setReason] = useState("");
  const canWrite = useHasPermission("documents:write");
  const canVerify = useHasPermission("documents:verify");
  const history = useDocumentHistory(document.id);
  const verify = useVerifyDocument(document.contact_id, document.id);
  const archive = useArchiveDocument(document.contact_id, document.id);
  const expire = useExpireDocument(document.contact_id, document.id);
  const content = useDocumentContent();
  const pending = verify.isPending || archive.isPending || expire.isPending;
  const mutationError = verify.error ?? archive.error ?? expire.error ?? content.error;

  function preview(versionId: string): void {
    content.mutate(
      { documentId: document.id, versionId },
      { onSuccess: ({ url }) => window.open(url, "_blank", "noopener,noreferrer") },
    );
  }

  function approve(): void {
    verify.mutate({ decision: "verified", expected_row_version: document.row_version });
  }

  function submitReason(): void {
    if (decision === "reject" && reason.trim()) {
      verify.mutate(
        {
          decision: "rejected",
          reason: reason.trim(),
          expected_row_version: document.row_version,
        },
        { onSuccess: () => setDecision(null) },
      );
    }
    if (decision === "archive") {
      archive.mutate(
        { reason: reason.trim() || undefined, expectedRowVersion: document.row_version },
        { onSuccess: () => setDecision(null) },
      );
    }
  }

  return (
    <Modal title={document.title} onClose={onClose} variant="sheet">
      <div className="space-y-5">
        <div className="rounded-2xl bg-[linear-gradient(135deg,var(--color-accent-soft),var(--color-bg-surface-2))] p-4">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface text-accent shadow-sm">
              <FileText aria-hidden className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={STATUS_TONE[document.status]} dot>{DOCUMENT_STATUS_LABELS[document.status]}</Badge>
                <Badge tone="neutral">{DOCUMENT_TYPE_LABELS[document.document_type]}</Badge>
              </div>
              <p className="mt-2 text-xs text-text-secondary">
                Version {document.current_version.version_no} · {document.version_count} retained {document.version_count === 1 ? "version" : "versions"}
              </p>
            </div>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-xs">
          <Info label="Created" value={formatDate(document.created_at)} />
          <Info label="Expiry" value={formatDate(document.expires_at)} warning={document.is_expired} />
          <Info label="Verified by" value={document.verified_by_name ?? "Not verified"} />
          <Info label="Last updated" value={formatDate(document.updated_at)} />
        </dl>

        {document.rejection_reason ? (
          <div className="flex gap-3 rounded-xl border border-danger/20 bg-danger/5 p-3">
            <ShieldAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
            <div><p className="text-xs font-semibold text-danger">Reviewer feedback</p><p className="mt-1 text-xs leading-relaxed text-text-secondary">{document.rejection_reason}</p></div>
          </div>
        ) : null}

        <section aria-labelledby="versions-heading">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div><h3 id="versions-heading" className="text-sm font-semibold text-text-primary">Version history</h3><p className="mt-0.5 text-xs text-text-secondary">Every submitted file remains immutable and traceable.</p></div>
            {canWrite && document.status !== "archived" ? <Button size="sm" variant="secondary" leftIcon={<Plus className="h-3.5 w-3.5" />} onClick={onAddVersion}>New version</Button> : null}
          </div>
          <div className="space-y-2">
            {[...document.versions].reverse().map((version, index) => (
              <div key={version.id} className="flex items-center gap-3 rounded-xl border border-border bg-surface-2 p-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-accent"><FileClock aria-hidden className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-text-primary">v{version.version_no} · {version.file_name ?? "Secure file"}</p>
                  <p className="mt-0.5 text-[11px] text-text-secondary">{formatBytes(version.byte_size)} · {version.uploaded_by_name ?? "System"} · {formatDate(version.created_at)}</p>
                  {version.note ? <p className="mt-1 text-[11px] text-text-secondary">{version.note}</p> : null}
                </div>
                {index === 0 ? <Badge tone="info">Current</Badge> : null}
                <Button size="sm" variant="ghost" aria-label={`Preview version ${version.version_no}`} onClick={() => preview(version.id)} loading={content.isPending} leftIcon={<ExternalLink className="h-3.5 w-3.5" />}>Open</Button>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="history-heading">
          <div className="mb-2 flex items-center gap-2"><History aria-hidden className="h-4 w-4 text-accent" /><h3 id="history-heading" className="text-sm font-semibold text-text-primary">Decision history</h3></div>
          {history.isLoading ? <Spinner label="Loading history…" /> : null}
          {history.isError ? <ErrorState message={apiErrorMessage(history.error)} onRetry={() => void history.refetch()} /> : null}
          {history.data ? (
            <ol className="relative ml-2 border-l border-border pl-5">
              {[...history.data].reverse().map((event) => (
                <li key={event.id} className="relative pb-4 last:pb-0">
                  <span className="absolute -left-[1.45rem] top-1 h-2.5 w-2.5 rounded-full border-2 border-surface bg-accent" />
                  <p className="text-xs font-semibold capitalize text-text-primary">{event.event_type.replaceAll("_", " ")}</p>
                  <p className="mt-0.5 text-[11px] text-text-secondary">{event.actor_name ?? "System"} · {formatDate(event.created_at)}</p>
                  {event.reason ? <p className="mt-1 text-xs text-text-secondary">{event.reason}</p> : null}
                </li>
              ))}
            </ol>
          ) : null}
        </section>

        {decision ? (
          <div className="rounded-xl border border-border bg-surface-2 p-3">
            <label className="text-xs font-semibold text-text-secondary">
              {decision === "reject" ? "Why does this need attention?" : "Archive note (optional)"}
              <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} autoFocus className="mt-1 w-full rounded-lg border border-border bg-surface p-2 text-sm text-text-primary outline-none focus:border-accent" />
            </label>
            <div className="mt-2 flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={() => setDecision(null)}>Cancel</Button><Button size="sm" variant={decision === "reject" ? "danger" : "secondary"} disabled={decision === "reject" && !reason.trim()} loading={pending} onClick={submitReason}>{decision === "reject" ? "Reject document" : "Archive"}</Button></div>
          </div>
        ) : null}
        {mutationError ? <p role="alert" className="text-sm text-danger">{apiErrorMessage(mutationError)}</p> : null}

        {!decision ? (
          <div className="sticky bottom-0 -mx-4 flex flex-wrap justify-end gap-2 border-t border-border bg-surface px-4 pt-3">
            {canWrite && document.status !== "archived" ? <Button size="sm" variant="ghost" leftIcon={<Archive className="h-3.5 w-3.5" />} onClick={() => setDecision("archive")}>Archive</Button> : null}
            {canVerify && document.status === "submitted" ? <><Button size="sm" variant="danger" leftIcon={<XCircle className="h-3.5 w-3.5" />} onClick={() => setDecision("reject")}>Needs attention</Button><Button size="sm" leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />} onClick={approve} loading={pending}>Verify</Button></> : null}
            {canVerify && document.status === "verified" && document.is_expired ? <Button size="sm" variant="secondary" leftIcon={<Clock3 className="h-3.5 w-3.5" />} onClick={() => expire.mutate({ expectedRowVersion: document.row_version })} loading={pending}>Mark expired</Button> : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

function Info({ label, value, warning = false }: { label: string; value: string; warning?: boolean }): JSX.Element {
  return <div className="rounded-xl border border-border bg-surface-2 p-3"><dt className="text-text-disabled">{label}</dt><dd className={`mt-1 font-semibold ${warning ? "text-warning" : "text-text-primary"}`}>{value}</dd></div>;
}
