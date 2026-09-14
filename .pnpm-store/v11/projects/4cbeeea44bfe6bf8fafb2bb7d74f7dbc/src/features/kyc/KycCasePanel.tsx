import {
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  FileLock2,
  History,
  ShieldCheck,
  UserRoundCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Modal, Skeleton } from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import { DocumentWorkspace } from "@/features/documents";
import { useContactDocuments } from "@/features/documents/api";
import {
  apiErrorMessage,
  useCreateKycAppointment,
  useKycDecisions,
  useRecordKycApproval,
  useRecordKycReview,
  useSetKycDocumentReference,
  useUpdateKycCase,
} from "@/features/kyc/api";
import {
  KYC_DOCUMENT_LABELS,
  KYC_REASON_LABELS,
  KYC_STATUS_LABELS,
  type KycDocumentPurpose,
  type KycOperationsCard,
  type KycReasonCode,
} from "@/features/kyc/types";
import { useCancelTask, useCompleteTask, useRescheduleTask } from "@/features/tasks/api";
import { useAuth, useHasPermission } from "@/lib/auth";

type Tab = "checks" | "documents" | "appointments" | "decisions";
const FIELD = "mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-focus/20 disabled:opacity-60";

export function KycCasePanel({ card, onClose }: { card: KycOperationsCard; onClose: () => void }): JSX.Element {
  const [tab, setTab] = useState<Tab>("checks");
  const tabs: Array<{ key: Tab; label: string; icon: typeof ClipboardCheck }> = [
    { key: "checks", label: "Verification", icon: ClipboardCheck },
    { key: "documents", label: "Documents", icon: FileLock2 },
    { key: "appointments", label: "Appointments", icon: CalendarClock },
    { key: "decisions", label: "Decisions", icon: History },
  ];
  return (
    <Modal title={`${card.contact_name} · KYC`} onClose={onClose} variant="drawer">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface-2 p-3">
          <div><p className="text-sm font-semibold text-text-primary">{card.contact_phone}</p><p className="mt-0.5 text-xs text-text-secondary">{card.owner_name ?? "Unassigned"} · version {card.row_version}</p></div>
          <div className="flex items-center gap-2"><StatusBadge status={card.status} /><Link className="inline-flex min-h-10 items-center rounded-lg border border-border px-3 text-xs font-semibold text-text-primary hover:bg-hover" to={`/contacts/${card.contact_id}`}>Customer 360</Link></div>
        </div>
        <div className="grid grid-cols-4 gap-1 rounded-xl border border-border bg-surface-2 p-1" role="tablist" aria-label="KYC case sections">
          {tabs.map(({ key, label, icon: Icon }) => <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)} className={`flex min-h-11 items-center justify-center gap-1.5 rounded-lg px-2 text-xs font-semibold ${tab === key ? "bg-surface text-accent shadow-sm" : "text-text-secondary hover:text-text-primary"}`}><Icon aria-hidden className="h-4 w-4" /><span className="hidden sm:inline">{label}</span></button>)}
        </div>
        {tab === "checks" ? <VerificationPanel card={card} /> : null}
        {tab === "documents" ? <DocumentsPanel card={card} /> : null}
        {tab === "appointments" ? <AppointmentsPanel card={card} /> : null}
        {tab === "decisions" ? <DecisionPanel card={card} /> : null}
      </div>
    </Modal>
  );
}

function VerificationPanel({ card }: { card: KycOperationsCard }): JSX.Element {
  const canWrite = useHasPermission("kyc:write");
  const readOnly = !canWrite || card.status === "approved" || card.status === "rejected";
  const [status, setStatus] = useState<"pending" | "documents_pending" | "under_review">(
    card.status === "approved" || card.status === "rejected" ? "under_review" : card.status,
  );
  const [holder, setHolder] = useState(card.holder_verified);
  const [delhi, setDelhi] = useState(card.delhi_presence_verified);
  const [active, setActive] = useState(card.active_delhi_number_verified);
  const [owner, setOwner] = useState(card.owner_user_id ?? "");
  const update = useUpdateKycCase();
  const users = useUsers(useHasPermission("users:read"));
  useEffect(() => { setHolder(card.holder_verified); setDelhi(card.delhi_presence_verified); setActive(card.active_delhi_number_verified); setOwner(card.owner_user_id ?? ""); if (card.status !== "approved" && card.status !== "rejected") setStatus(card.status); }, [card]);
  const checks = [
    { label: "Original Vi holder verified", detail: "Evidence matches the original account holder.", value: holder, set: setHolder },
    { label: "Delhi presence verified", detail: "Customer presence in the approved service area is evidenced.", value: delhi, set: setDelhi },
    { label: "Active number verified", detail: "An active Delhi number is available for the governed hand-off.", value: active, set: setActive },
  ];
  return <div role="tabpanel" className="space-y-4">
    <section className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-text-primary">Verification progress</h3><p className="mt-1 text-xs text-text-secondary">{card.progress_percent}% complete · all checks and both protected document references are required.</p></div><span className="text-lg font-bold text-accent">{card.progress_percent}%</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-2" aria-label={`${card.progress_percent}% complete`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={card.progress_percent}><span className="block h-full rounded-full bg-accent transition-all" style={{ width: `${card.progress_percent}%` }} /></div></section>
    <section className="rounded-xl border border-border p-4"><div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-medium text-text-secondary">Preparation status<select className={FIELD} value={status} disabled={readOnly} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="pending">Pending</option><option value="documents_pending">Documents pending</option><option value="under_review">Under review</option></select></label><label className="text-xs font-medium text-text-secondary">Case owner<select className={FIELD} value={owner} disabled={readOnly} onChange={(event) => setOwner(event.target.value)}><option value="">Unassigned</option>{(users.data?.data ?? []).filter((user) => user.is_active).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}</select></label></div><div className="mt-4 space-y-2">{checks.map((check) => <label key={check.label} className="flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border border-border bg-surface-2 p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus"><input type="checkbox" checked={check.value} disabled={readOnly} onChange={(event) => check.set(event.target.checked)} className="h-4 w-4 accent-[var(--color-accent)]" /><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-text-primary">{check.label}</span><span className="block text-xs text-text-secondary">{check.detail}</span></span>{check.value ? <CheckCircle2 aria-label="Verified" className="h-5 w-5 text-success" /> : <span className="text-xs font-semibold text-warning">Required</span>}</label>)}</div>{update.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(update.error)} /></div> : null}<div className="mt-4 flex items-center justify-between gap-3"><p className="text-xs text-text-secondary">{readOnly ? "Read-only: your role or the final decision prevents edits." : "Saving uses optimistic concurrency and writes audit/Timeline evidence."}</p>{!readOnly ? <Button loading={update.isPending} onClick={() => update.mutate({ kycId: card.id, expectedRowVersion: card.row_version, status, ownerUserId: owner || null, holderVerified: holder, delhiPresenceVerified: delhi, activeDelhiNumberVerified: active })}>Save verification</Button> : null}</div></section>
  </div>;
}

function DocumentsPanel({ card }: { card: KycOperationsCard }): JSX.Element {
  const canWrite = useHasPermission("kyc:write") && card.status !== "approved" && card.status !== "rejected";
  const canReadDocuments = useHasPermission("documents:read");
  const documents = useContactDocuments(card.contact_id, { q: "", status: "", type: "" });
  const setReference = useSetKycDocumentReference();
  const options = useMemo(() => (documents.data?.data ?? []).filter((document) => document.document_type === "identity" || document.document_type === "address"), [documents.data?.data]);
  return <div role="tabpanel" className="space-y-4"><section className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-text-primary">Governed document checklist</h3><p className="mt-1 text-xs text-text-secondary">References point to protected Document Center records. Aadhaar and PAN numbers are never collected here.</p></div><Badge tone={card.checklist_complete ? "success" : "warning"}>{card.checklist_complete ? "Complete" : "Missing evidence"}</Badge></div>{!canReadDocuments ? <div className="mt-3"><EmptyState compact title="Protected document access denied" description="Your role can view KYC status but cannot inspect or link customer documents." /></div> : documents.isLoading ? <div className="mt-3 space-y-2"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div> : documents.isError ? <div className="mt-3"><ErrorState message={apiErrorMessage(documents.error)} onRetry={() => void documents.refetch()} /></div> : <div className="mt-3 space-y-3">{(["aadhaar", "pan"] as KycDocumentPurpose[]).map((purpose) => { const current = card.checklist.find((item) => item.purpose === purpose); return <div key={purpose} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-sm font-semibold text-text-primary">{KYC_DOCUMENT_LABELS[purpose]}</p><p className="mt-0.5 text-xs text-text-secondary">{current ? `${current.document_title} · ${current.document_status}` : "No protected reference linked"}</p></div><Badge tone={current?.document_status === "verified" ? "success" : current ? "warning" : "neutral"}>{current?.document_status ?? "Missing"}</Badge></div>{canWrite ? <div className="mt-3 flex gap-2"><label className="min-w-0 flex-1 text-xs font-medium text-text-secondary"><span className="sr-only">Select {KYC_DOCUMENT_LABELS[purpose]}</span><select className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary" defaultValue={current?.document_id ?? ""} onChange={(event) => { if (event.target.value) setReference.mutate({ kycId: card.id, purpose, documentId: event.target.value, expectedRowVersion: card.row_version }); }}><option value="">Select governed document</option>{options.map((document) => <option key={document.id} value={document.id}>{document.title} · {document.status}</option>)}</select></label></div> : null}</div>; })}{options.length === 0 ? <EmptyState compact title="No identity documents available" description="Add Aadhaar/PAN evidence through the protected Document Center, then link it here." /> : null}</div>}{setReference.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(setReference.error)} /></div> : null}</section><section className="rounded-xl border border-border p-3"><DocumentWorkspace contactId={card.contact_id} compact /></section></div>;
}

function AppointmentsPanel({ card }: { card: KycOperationsCard }): JSX.Element {
  const canWriteKyc = useHasPermission("kyc:write");
  const canWriteTasks = useHasPermission("tasks:write");
  const canWrite = canWriteKyc && canWriteTasks && card.status !== "approved" && card.status !== "rejected";
  const [due, setDue] = useState("");
  const [description, setDescription] = useState("");
  const create = useCreateKycAppointment();
  const complete = useCompleteTask();
  const cancel = useCancelTask();
  const reschedule = useRescheduleTask();
  const [rescheduleId, setRescheduleId] = useState<string | null>(null);
  return <div role="tabpanel" className="space-y-4"><section className="rounded-xl border border-border p-4"><div><h3 className="text-sm font-semibold text-text-primary">Verification appointments</h3><p className="mt-1 text-xs text-text-secondary">Scheduling is backed by the shared Task authority; reschedules, completion and cancellation remain in immutable Task history.</p></div>{card.appointments.length === 0 ? <div className="mt-3"><EmptyState compact title="No KYC appointment scheduled" description="Schedule a verification meeting when the customer and reviewer are ready." /></div> : <ol className="mt-3 space-y-2">{card.appointments.map((appointment) => <li key={appointment.id} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-sm font-semibold text-text-primary">{new Date(appointment.due_at).toLocaleString()}</p><p className="mt-0.5 text-xs text-text-secondary">{appointment.assigned_agent_name ?? "Assigned reviewer"} · version {appointment.row_version}</p></div><Badge tone={appointment.status === "completed" ? "success" : appointment.status === "cancelled" ? "neutral" : "info"}>{appointment.status}</Badge></div>{canWrite && appointment.status === "open" ? <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="secondary" onClick={() => setRescheduleId(rescheduleId === appointment.id ? null : appointment.id)}>Reschedule</Button><Button size="sm" variant="secondary" loading={complete.isPending} onClick={() => complete.mutate({ taskId: appointment.id, expectedRowVersion: appointment.row_version, completionNotes: "KYC appointment completed", createTimelineNote: true })}>Complete</Button><Button size="sm" variant="ghost" loading={cancel.isPending} onClick={() => cancel.mutate({ taskId: appointment.id, expectedRowVersion: appointment.row_version, reason: "KYC appointment cancelled" })}>Cancel</Button></div> : null}{rescheduleId === appointment.id ? <div className="mt-3 flex gap-2"><input aria-label="New appointment date and time" type="datetime-local" className="h-10 min-w-0 flex-1 rounded-lg border border-border bg-surface px-3 text-sm" onChange={(event) => setDue(event.target.value)} /><Button size="sm" disabled={!due} loading={reschedule.isPending} onClick={() => reschedule.mutate({ taskId: appointment.id, dueAt: new Date(due).toISOString(), expectedRowVersion: appointment.row_version }, { onSuccess: () => { setDue(""); setRescheduleId(null); } })}>Save</Button></div> : null}</li>)}</ol>}{canWrite ? <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><label className="text-xs font-medium text-text-secondary">Date and time<input type="datetime-local" value={due} onChange={(event) => setDue(event.target.value)} className={FIELD} /></label><label className="text-xs font-medium text-text-secondary">Preparation note<input value={description} onChange={(event) => setDescription(event.target.value)} className={FIELD} placeholder="Access or preparation details" /></label><Button className="self-end" disabled={!due} loading={create.isPending} onClick={() => create.mutate({ kycId: card.id, expectedRowVersion: card.row_version, dueAt: new Date(due).toISOString(), description }, { onSuccess: () => { setDue(""); setDescription(""); } })}>Schedule</Button></div> : <p className="mt-3 text-xs text-warning">Read-only: KYC and Task write permissions are required.</p>}{create.error || complete.error || cancel.error || reschedule.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(create.error ?? complete.error ?? cancel.error ?? reschedule.error)} /></div> : null}</section></div>;
}

function DecisionPanel({ card }: { card: KycOperationsCard }): JSX.Element {
  const decisions = useKycDecisions(card.id);
  const review = useRecordKycReview();
  const approval = useRecordKycApproval();
  const { user } = useAuth();
  const canReview = useHasPermission("kyc:decide") && user?.id !== card.requester_user_id && card.status !== "approved" && card.status !== "rejected";
  const canApprove = useHasPermission("kyc:approve") && Boolean(card.latest_review?.decision === "approved") && (!card.latest_manager_decision || new Date(card.latest_review?.decided_at ?? 0) > new Date(card.latest_manager_decision.decided_at)) && user?.id !== card.requester_user_id && user?.id !== card.latest_review?.decided_by && card.status !== "approved" && card.status !== "rejected";
  const [decision, setDecision] = useState<"approved" | "rejected" | "needs_information">("approved");
  const [reasonCode, setReasonCode] = useState<KycReasonCode>("document_mismatch");
  const [reason, setReason] = useState("");
  const submit = (manager: boolean): void => { const mutation = manager ? approval : review; mutation.mutate({ kycId: card.id, expectedRowVersion: card.row_version, decision, reasonCode: decision === "approved" ? null : reasonCode, reason: decision === "approved" ? null : reason }); };
  return <div role="tabpanel" className="space-y-4"><section className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-text-primary">Separation of duties</h3><p className="mt-1 text-xs text-text-secondary">The requester, reviewer and manager approver must be different users. Every decision is immutable.</p></div><UserRoundCheck aria-hidden className="h-5 w-5 text-accent" /></div><div className="mt-3 grid gap-2 sm:grid-cols-2"><Boundary label="Reviewer" value={card.latest_review?.decision ?? "Awaiting review"} ready={card.latest_review?.decision === "approved"} /><Boundary label="Manager approval" value={card.latest_manager_decision?.decision ?? "Awaiting approval"} ready={card.latest_manager_decision?.decision === "approved"} /></div></section><section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold text-text-primary">Decision history</h3>{decisions.isLoading ? <Skeleton className="mt-3 h-28 w-full" /> : decisions.isError ? <div className="mt-3"><ErrorState message={apiErrorMessage(decisions.error)} onRetry={() => void decisions.refetch()} /></div> : (decisions.data ?? []).length === 0 ? <div className="mt-3"><EmptyState compact title="No decisions recorded" /></div> : <ol className="mt-3 space-y-2">{(decisions.data ?? []).slice().reverse().map((item) => <li key={item.id} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><p className="text-sm font-semibold capitalize text-text-primary">{item.decision_type.replaceAll("_", " ")}</p><Badge tone={item.decision === "approved" ? "success" : item.decision === "rejected" ? "danger" : "warning"}>{item.decision.replaceAll("_", " ")}</Badge></div><p className="mt-1 text-xs text-text-secondary">{new Date(item.decided_at).toLocaleString()} · actor {item.decided_by?.slice(0, 8) ?? "system"}</p>{item.reason_code ? <p className="mt-2 text-xs font-semibold text-text-primary">{KYC_REASON_LABELS[item.reason_code]}</p> : null}{item.reason ? <p className="mt-1 text-xs text-text-secondary">{item.reason}</p> : null}</li>)}</ol>}</section>{canReview || canApprove ? <section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold text-text-primary">Record governed decision</h3><div className="mt-3 grid gap-3"><label className="text-xs font-medium text-text-secondary">Outcome<select className={FIELD} value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)}><option value="approved">Approve</option><option value="needs_information">Request information</option><option value="rejected">Reject</option></select></label>{decision !== "approved" ? <><label className="text-xs font-medium text-text-secondary">Structured reason<select className={FIELD} value={reasonCode} onChange={(event) => setReasonCode(event.target.value as KycReasonCode)}>{Object.entries(KYC_REASON_LABELS).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label><label className="text-xs font-medium text-text-secondary">Decision explanation<textarea className={`${FIELD} h-auto py-2`} rows={3} value={reason} onChange={(event) => setReason(event.target.value)} /></label></> : null}</div><div className="mt-4 flex flex-wrap justify-end gap-2">{canReview ? <Button variant="secondary" disabled={decision !== "approved" && !reason.trim()} loading={review.isPending} onClick={() => submit(false)}>Record reviewer decision</Button> : null}{canApprove ? <Button disabled={decision !== "approved" && !reason.trim()} loading={approval.isPending} leftIcon={<ShieldCheck className="h-4 w-4" />} onClick={() => submit(true)}>Record manager decision</Button> : null}</div>{review.error || approval.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(review.error ?? approval.error)} /></div> : null}</section> : <section className="rounded-xl border border-border bg-surface-2 p-4"><p className="text-sm font-semibold text-text-primary">Decision controls are read-only</p><p className="mt-1 text-xs text-text-secondary">Your permission or separation-of-duty boundary does not permit a decision at this stage.</p></section>}</div>;
}

function Boundary({ label, value, ready }: { label: string; value: string; ready: boolean }): JSX.Element { return <div className="rounded-xl border border-border bg-surface-2 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-text-disabled">{label}</p><p className="mt-1 flex items-center gap-2 text-sm font-semibold capitalize text-text-primary">{ready ? <CheckCircle2 className="h-4 w-4 text-success" /> : <ShieldCheck className="h-4 w-4 text-text-disabled" />}{value.replaceAll("_", " ")}</p></div>; }
function StatusBadge({ status }: { status: KycOperationsCard["status"] }): JSX.Element { return <Badge tone={status === "approved" ? "success" : status === "rejected" ? "danger" : status === "under_review" ? "info" : "warning"} dot>{KYC_STATUS_LABELS[status]}</Badge>; }
