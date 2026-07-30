import {
  Archive,
  CheckCircle2,
  ChevronRight,
  FileSearch,
  FileText,
  FolderLock,
  Plus,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import { apiErrorMessage, useContactDocuments } from "@/features/documents/api";
import { DocumentDetailDialog } from "@/features/documents/DocumentDetailDialog";
import { DocumentFormDialog } from "@/features/documents/DocumentFormDialog";
import {
  DOCUMENT_STATUSES,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_LABELS,
  type CustomerDocument,
  type DocumentFilters,
  type DocumentStatus,
  type DocumentType,
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

const INITIAL_FILTERS: DocumentFilters = { q: "", status: "", type: "" };

interface Props {
  contactId: string;
  compact?: boolean;
}

export function DocumentWorkspace({ contactId, compact = false }: Props): JSX.Element {
  const [filters, setFilters] = useState<DocumentFilters>(INITIAL_FILTERS);
  const [creating, setCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [versioningId, setVersioningId] = useState<string | null>(null);
  const canRead = useHasPermission("documents:read");
  const canWrite = useHasPermission("documents:write");
  const query = useContactDocuments(canRead ? contactId : "", filters);
  const documents = useMemo(() => query.data?.data ?? [], [query.data]);
  const selected = documents.find((document) => document.id === selectedId) ?? null;
  const versioning = documents.find((document) => document.id === versioningId) ?? null;
  const counts = useMemo(
    () => ({
      total: query.data?.total ?? 0,
      submitted: documents.filter((document) => document.status === "submitted").length,
      verified: documents.filter((document) => document.status === "verified" && !document.is_expired).length,
      attention: documents.filter((document) => document.status === "rejected" || document.is_expired).length,
    }),
    [documents, query.data?.total],
  );

  if (!canRead) {
    return <EmptyState icon={<FolderLock className="h-6 w-6" />} title="Document access is restricted" description="Your role does not include permission to view customer documents." />;
  }

  return (
    <div className="space-y-4">
      {!compact ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={FolderLock} label="Secure documents" value={counts.total} tone="accent" />
          <Metric icon={FileSearch} label="Awaiting review" value={counts.submitted} tone="warning" />
          <Metric icon={ShieldCheck} label="Verified" value={counts.verified} tone="success" />
          <Metric icon={TriangleAlert} label="Needs attention" value={counts.attention} tone="danger" />
        </div>
      ) : null}

      <Card className="overflow-hidden" padding={false}>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2"><FolderLock aria-hidden className="h-4 w-4 text-accent" /><h2 className="text-sm font-semibold text-text-primary">Customer documents</h2></div>
            <p className="mt-1 text-xs text-text-secondary">Immutable versions, reviewer decisions, expiry, and signed previews in one governed record.</p>
          </div>
          {canWrite ? <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>Add document</Button> : null}
        </div>

        <div className="grid gap-2 border-b border-border bg-surface-2/60 p-3 sm:grid-cols-[minmax(12rem,1fr)_12rem_12rem]">
          <label className="flex h-10 items-center gap-2 rounded-lg border border-border bg-surface px-3">
            <Search aria-hidden className="h-4 w-4 text-text-disabled" />
            <span className="sr-only">Search documents</span>
            <input value={filters.q} onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} placeholder="Search document name" className="w-full bg-transparent text-sm text-text-primary outline-none placeholder:text-text-disabled" />
          </label>
          <select aria-label="Filter by status" value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as DocumentStatus | "" }))} className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-accent">
            <option value="">All statuses</option>
            {DOCUMENT_STATUSES.map((status) => <option key={status} value={status}>{DOCUMENT_STATUS_LABELS[status]}</option>)}
          </select>
          <select aria-label="Filter by category" value={filters.type} onChange={(event) => setFilters((current) => ({ ...current, type: event.target.value as DocumentType | "" }))} className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-accent">
            <option value="">All categories</option>
            {DOCUMENT_TYPES.map((type) => <option key={type} value={type}>{DOCUMENT_TYPE_LABELS[type]}</option>)}
          </select>
        </div>

        {query.isLoading ? <div className="space-y-2 p-4"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div> : null}
        {query.isError ? <div className="p-4"><ErrorState message={apiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></div> : null}
        {!query.isLoading && !query.isError && documents.length === 0 ? (
          <div className="p-6"><EmptyState icon={<FileText className="h-7 w-7" />} title={filters.q || filters.status || filters.type ? "No documents match" : "No customer documents yet"} description={filters.q || filters.status || filters.type ? "Clear a filter or try another document name." : canWrite ? "Add the first secure file to start a traceable review history." : "No governed documents have been added for this customer."} action={canWrite && !(filters.q || filters.status || filters.type) ? <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>Add first document</Button> : undefined} /></div>
        ) : null}
        {documents.length > 0 ? (
          <div className="divide-y divide-border">
            {documents.map((document) => <DocumentRow key={document.id} document={document} onOpen={() => setSelectedId(document.id)} />)}
          </div>
        ) : null}
        {documents.length > 0 ? <div className="flex items-center justify-between border-t border-border bg-surface-2/40 px-4 py-3 text-xs text-text-secondary"><span>{documents.length} of {query.data?.total ?? documents.length} documents</span><span className="flex items-center gap-1"><CheckCircle2 aria-hidden className="h-3.5 w-3.5 text-success" />Signed previews only</span></div> : null}
      </Card>

      {creating ? <DocumentFormDialog contactId={contactId} onClose={() => setCreating(false)} onSaved={(document) => { setCreating(false); setSelectedId(document.id); }} /> : null}
      {selected ? <DocumentDetailDialog document={selected} onClose={() => setSelectedId(null)} onAddVersion={() => { setSelectedId(null); setVersioningId(selected.id); }} /> : null}
      {versioning ? <DocumentFormDialog contactId={contactId} document={versioning} onClose={() => setVersioningId(null)} onSaved={(document) => { setVersioningId(null); setSelectedId(document.id); }} /> : null}
    </div>
  );
}

function DocumentRow({ document, onOpen }: { document: CustomerDocument; onOpen: () => void }): JSX.Element {
  return (
    <button type="button" onClick={onOpen} className="group grid w-full gap-3 p-4 text-left transition hover:bg-hover sm:grid-cols-[minmax(0,1.4fr)_minmax(9rem,.7fr)_minmax(8rem,.6fr)_auto] sm:items-center">
      <span className="flex min-w-0 items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent"><FileText aria-hidden className="h-4 w-4" /></span>
        <span className="min-w-0"><span className="block truncate text-sm font-semibold text-text-primary">{document.title}</span><span className="mt-0.5 block truncate text-xs text-text-secondary">{document.current_version.file_name ?? document.current_version.mime_type} · {formatBytes(document.current_version.byte_size)}</span></span>
      </span>
      <span><Badge tone={STATUS_TONE[document.status]} dot>{DOCUMENT_STATUS_LABELS[document.status]}</Badge>{document.is_expired && document.status !== "expired" ? <span className="ml-1 text-[11px] font-semibold text-warning">Past expiry</span> : null}</span>
      <span className="text-xs text-text-secondary"><span className="block font-medium text-text-primary">{DOCUMENT_TYPE_LABELS[document.document_type]}</span><span className="mt-0.5 block">v{document.current_version.version_no} · {document.version_count} total</span></span>
      <ChevronRight aria-hidden className="hidden h-4 w-4 text-text-disabled transition group-hover:translate-x-0.5 group-hover:text-accent sm:block" />
    </button>
  );
}

const METRIC_TONES = {
  accent: "bg-accent-soft text-accent",
  warning: "bg-warning/10 text-warning",
  success: "bg-success/10 text-success",
  danger: "bg-danger/10 text-danger",
};

function Metric({ icon: Icon, label, value, tone }: { icon: typeof Archive; label: string; value: number; tone: keyof typeof METRIC_TONES }): JSX.Element {
  return <Card className="flex items-center gap-3 p-4" padding={false}><span className={`flex h-10 w-10 items-center justify-center rounded-xl ${METRIC_TONES[tone]}`}><Icon aria-hidden className="h-4 w-4" /></span><div><p className="text-xl font-bold tracking-tight text-text-primary">{value}</p><p className="text-xs font-medium text-text-secondary">{label}</p></div></Card>;
}
