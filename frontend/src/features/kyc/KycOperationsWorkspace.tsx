import {
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileWarning,
  RefreshCw,
  Search,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { apiErrorMessage, useKycOperations } from "@/features/kyc/api";
import { KycCasePanel } from "@/features/kyc/KycCasePanel";
import { KYC_STATUS_LABELS, type KycOperationsCard, type KycStatus } from "@/features/kyc/types";
import { useHasPermission } from "@/lib/auth";

const STATUS_TABS: Array<{ value: KycStatus | ""; label: string }> = [
  { value: "", label: "All cases" },
  { value: "documents_pending", label: "Documents" },
  { value: "under_review", label: "Review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export function KycOperationsWorkspace(): JSX.Element {
  const canRead = useHasPermission("kyc:read");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<KycStatus | "">("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const query = useKycOperations({ q: q.trim() || undefined, kyc_status: status ? [status] : undefined, limit: 200 });
  const rows = useMemo(() => query.data?.data ?? [], [query.data?.data]);
  const selected = rows.find((row) => row.id === selectedId) ?? null;
  const counts = useMemo(() => ({
    total: query.data?.total ?? 0,
    review: rows.filter((row) => row.status === "under_review").length,
    missing: rows.filter((row) => !row.checklist_complete).length,
    approved: rows.filter((row) => row.status === "approved").length,
  }), [query.data?.total, rows]);

  if (!canRead) return <EmptyState icon={<ShieldCheck className="h-7 w-7" />} title="KYC operations are restricted" description="Your role does not include permission to view KYC cases." />;

  return <div className="space-y-5">
    <section aria-label="KYC operating summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric icon={UsersRound} label="Visible cases" value={counts.total} detail="Tenant-scoped records" />
      <Metric icon={ClipboardCheck} label="Under review" value={counts.review} detail="Awaiting reviewer action" />
      <Metric icon={FileWarning} label="Missing evidence" value={counts.missing} detail="Aadhaar or PAN reference" warning />
      <Metric icon={CheckCircle2} label="Approved" value={counts.approved} detail="Manager-approved cases" success />
    </section>

    <Card className="overflow-hidden" padding={false}>
      <div className="border-b border-border p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <label className="relative block w-full lg:max-w-md"><span className="sr-only">Search KYC cases</span><Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-disabled" /><input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search customer, email or mobile" className="h-11 w-full rounded-xl border border-border bg-surface-2 pl-10 pr-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-focus/20" /></label>
          <Button variant="secondary" leftIcon={<RefreshCw className="h-4 w-4" />} onClick={() => void query.refetch()} loading={query.isFetching}>Refresh</Button>
        </div>
        <div className="mt-4 flex gap-1 overflow-x-auto border-b border-border" role="tablist" aria-label="KYC status filters">
          {STATUS_TABS.map((item) => <button key={item.value || "all"} type="button" role="tab" aria-selected={status === item.value} onClick={() => setStatus(item.value)} className={`min-h-11 shrink-0 border-b-2 px-4 text-sm font-semibold transition-colors ${status === item.value ? "border-accent text-accent" : "border-transparent text-text-secondary hover:text-text-primary"}`}>{item.label}</button>)}
        </div>
      </div>

      {query.isLoading ? <LoadingTable /> : query.isError ? <div className="p-6"><ErrorState message={apiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></div> : rows.length === 0 ? <div className="p-8"><EmptyState icon={<ClipboardCheck className="h-7 w-7" />} title={q || status ? "No KYC cases match these filters" : "No KYC cases yet"} description={q || status ? "Clear or adjust the search and status filter." : "Open KYC from an eligible Reactivation case; no placeholder records are shown."} action={q || status ? <Button variant="secondary" onClick={() => { setQ(""); setStatus(""); }}>Clear filters</Button> : undefined} /></div> : <><DesktopTable rows={rows} onSelect={setSelectedId} /><MobileCards rows={rows} onSelect={setSelectedId} /><div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-text-secondary"><span>{rows.length} visible of {query.data?.total ?? rows.length}</span><span>Real-time governed projection</span></div></>}
    </Card>
    {selected ? <KycCasePanel card={selected} onClose={() => setSelectedId(null)} /> : null}
  </div>;
}

function DesktopTable({ rows, onSelect }: { rows: KycOperationsCard[]; onSelect: (id: string) => void }): JSX.Element {
  return <div className="hidden overflow-x-auto md:block"><table className="w-full min-w-[980px] border-collapse text-left"><thead className="bg-surface-2 text-[11px] font-semibold uppercase tracking-wide text-text-disabled"><tr><th className="px-5 py-3">Customer</th><th className="px-4 py-3">Progress</th><th className="px-4 py-3">Checklist</th><th className="px-4 py-3">Appointment</th><th className="px-4 py-3">SLA</th><th className="px-4 py-3">Status</th><th className="w-12 px-4 py-3"><span className="sr-only">Open</span></th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} tabIndex={0} onClick={() => onSelect(row.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(row.id); } }} className="cursor-pointer border-t border-border bg-surface transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"><td className="px-5 py-4"><p className="text-sm font-semibold text-text-primary">{row.contact_name}</p><p className="mt-0.5 text-xs text-text-secondary">{row.contact_phone}{row.owner_name ? ` · ${row.owner_name}` : " · Unassigned"}</p></td><td className="px-4 py-4"><div className="flex items-center gap-2"><div className="h-1.5 w-20 overflow-hidden rounded-full bg-surface-2"><span className="block h-full rounded-full bg-accent" style={{ width: `${row.progress_percent}%` }} /></div><span className="text-xs font-semibold text-text-primary">{row.progress_percent}%</span></div></td><td className="px-4 py-4"><Badge tone={row.checklist_complete ? "success" : "warning"}>{row.checklist_complete ? "Complete" : `${row.checklist.length}/2 linked`}</Badge></td><td className="px-4 py-4"><AppointmentValue row={row} /></td><td className="px-4 py-4"><Badge tone={row.sla_status === "breached" ? "danger" : row.sla_status === "on_track" ? "success" : "neutral"}>{row.sla_status.replaceAll("_", " ")}</Badge></td><td className="px-4 py-4"><StatusBadge status={row.status} /></td><td className="px-4 py-4"><ChevronRight aria-hidden className="h-4 w-4 text-text-disabled" /></td></tr>)}</tbody></table></div>;
}

function MobileCards({ rows, onSelect }: { rows: KycOperationsCard[]; onSelect: (id: string) => void }): JSX.Element { return <ul className="divide-y divide-border md:hidden">{rows.map((row) => <li key={row.id}><button type="button" onClick={() => onSelect(row.id)} className="w-full p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-text-primary">{row.contact_name}</p><p className="mt-0.5 text-xs text-text-secondary">{row.contact_phone}</p></div><StatusBadge status={row.status} /></div><div className="mt-3 grid grid-cols-2 gap-2"><Fact label="Progress" value={`${row.progress_percent}%`} /><Fact label="Documents" value={row.checklist_complete ? "Complete" : `${row.checklist.length}/2 linked`} /><Fact label="Owner" value={row.owner_name ?? "Unassigned"} /><Fact label="SLA" value={row.sla_status.replaceAll("_", " ")} /></div><div className="mt-3 flex items-center justify-between border-t border-border pt-3"><AppointmentValue row={row} /><span className="inline-flex items-center gap-1 text-xs font-semibold text-accent">Open case <ChevronRight className="h-4 w-4" /></span></div></button></li>)}</ul>; }
function Metric({ icon: Icon, label, value, detail, warning = false, success = false }: { icon: typeof UsersRound; label: string; value: number; detail: string; warning?: boolean; success?: boolean }): JSX.Element { return <Card className="flex items-center gap-3 p-4" padding={false}><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${warning ? "bg-warning/10 text-warning" : success ? "bg-success/10 text-success" : "bg-accent-soft text-accent"}`}><Icon aria-hidden className="h-5 w-5" /></span><span className="min-w-0"><span className="block text-xl font-bold text-text-primary">{value}</span><span className="block text-xs font-semibold text-text-primary">{label}</span><span className="block truncate text-[11px] text-text-secondary">{detail}</span></span></Card>; }
function StatusBadge({ status }: { status: KycStatus }): JSX.Element { return <Badge tone={status === "approved" ? "success" : status === "rejected" ? "danger" : status === "under_review" ? "info" : "warning"} dot>{KYC_STATUS_LABELS[status]}</Badge>; }
function AppointmentValue({ row }: { row: KycOperationsCard }): JSX.Element { const appointment = row.appointments.find((item) => item.status === "open") ?? row.appointments[0]; return appointment ? <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary"><CalendarClock className="h-4 w-4" />{new Date(appointment.due_at).toLocaleDateString()}</span> : <span className="text-xs text-text-disabled">Not scheduled</span>; }
function Fact({ label, value }: { label: string; value: string }): JSX.Element { return <span className="rounded-lg bg-surface-2 p-2"><span className="block text-[10px] font-semibold uppercase tracking-wide text-text-disabled">{label}</span><span className="mt-0.5 block truncate text-xs font-semibold capitalize text-text-primary">{value}</span></span>; }
function LoadingTable(): JSX.Element { return <div className="space-y-2 p-4" aria-label="Loading KYC cases"><Skeleton className="h-12 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>; }
