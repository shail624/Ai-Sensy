import {
  CalendarClock,
  CheckCircle2,
  FileText,
  History,
  Link2,
  ListChecks,
  MessageSquareText,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Modal, Skeleton } from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import { DocumentWorkspace } from "@/features/documents";
import { apiErrorMessage as kycErrorMessage, useContactKycCases, useCreateKycCase } from "@/features/kyc/api";
import { KYC_STATUS_LABELS } from "@/features/kyc/types";
import {
  apiErrorMessage,
  useAddReactivationNote,
  useEligibilityChecks,
  useReactivationEvents,
  useReactivationNotes,
  useRecordEligibility,
  useUpdateReactivation,
} from "@/features/reactivation/api";
import {
  REACTIVATION_STAGE_LABELS,
  REACTIVATION_STAGES,
  REACTIVATION_LABEL_NAMES,
  REACTIVATION_LABELS,
  type ReactivationCard,
  type ReactivationLabel,
  type ReactivationStage,
} from "@/features/reactivation/types";
import { TasksSectionForProfile } from "@/features/tasks/TasksSectionForProfile";
import { TaskActions } from "@/features/tasks/TaskActions";
import { useAuth, useHasPermission } from "@/lib/auth";

type DrawerTab = "overview" | "activity" | "work" | "documents" | "kyc";

const FIELD =
  "h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-focus/20";

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export interface ReactivationCaseDrawerProps {
  card: ReactivationCard;
  onClose: () => void;
  onMove: (card: ReactivationCard, target: ReactivationStage) => void;
}

export function ReactivationCaseDrawer({
  card,
  onClose,
  onMove,
}: ReactivationCaseDrawerProps): JSX.Element {
  const [tab, setTab] = useState<DrawerTab>("overview");
  const [ownerId, setOwnerId] = useState(card.owner_user_id ?? "");
  const [previousNumber, setPreviousNumber] = useState(card.previous_vi_number ?? "");
  const [activeNumber, setActiveNumber] = useState(card.active_delhi_number ?? "");
  const [labels, setLabels] = useState<ReactivationLabel[]>([...card.labels]);
  const [followUpAt, setFollowUpAt] = useState(toLocalInput(card.follow_up_at));
  const [releaseAt, setReleaseAt] = useState(toLocalInput(card.release_at));
  const canWrite = useHasPermission("reactivation:write");
  const canTransition = useHasPermission("reactivation:transition");
  const canReadUsers = useHasPermission("users:read");
  const { user } = useAuth();
  const users = useUsers(canReadUsers);
  const update = useUpdateReactivation();

  useEffect(() => {
    setOwnerId(card.owner_user_id ?? "");
    setPreviousNumber(card.previous_vi_number ?? "");
    setActiveNumber(card.active_delhi_number ?? "");
    setLabels([...card.labels]);
    setFollowUpAt(toLocalInput(card.follow_up_at));
    setReleaseAt(toLocalInput(card.release_at));
  }, [card]);

  const assignees = useMemo(() => {
    const rows = users.data?.data ?? [];
    if (rows.length > 0) return rows.filter((candidate) => candidate.is_active);
    if (!user) return [];
    return [
      {
        id: user.id,
        full_name: user.full_name,
        is_active: true,
      },
    ];
  }, [user, users.data?.data]);

  const saveOwnership = (): void => {
    update.mutate({
      card,
      ownerUserId: ownerId || null,
      previousViNumber: previousNumber.trim() || null,
      activeDelhiNumber: activeNumber.trim() || null,
      labels,
      followUpAt: labels.includes("follow_up") && followUpAt ? new Date(followUpAt).toISOString() : null,
      releaseAt: labels.includes("name_change") && releaseAt ? new Date(releaseAt).toISOString() : null,
    });
  };

  const toggleLabel = (label: ReactivationLabel): void => {
    setLabels((current) => current.includes(label) ? current.filter((item) => item !== label) : [...current, label]);
  };

  const missingRequiredDate = (labels.includes("follow_up") && !followUpAt) || (labels.includes("name_change") && !releaseAt);

  const tabs: Array<{ key: DrawerTab; label: string; icon: typeof UserRound }> = [
    { key: "overview", label: "Case", icon: UserRound },
    { key: "activity", label: "History", icon: History },
    { key: "work", label: "Tasks", icon: ListChecks },
    { key: "documents", label: "Documents", icon: FileText },
    { key: "kyc", label: "KYC", icon: ShieldAlert },
  ];

  return (
    <Modal title={`${card.contact_name} · ${REACTIVATION_STAGE_LABELS[card.stage]}`} onClose={onClose} variant="drawer">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-border bg-surface-2 p-3">
          <div>
            <p className="text-sm font-semibold text-text-primary">{card.contact_phone}</p>
            <p className="mt-0.5 text-xs text-text-secondary">
              {card.owner_name ? `Owned by ${card.owner_name}` : "Unassigned"} · v{card.row_version}
            </p>
          </div>
          <Link to={`/contacts/${card.contact_id}`} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border px-3 text-xs font-semibold text-text-primary hover:bg-hover">
            <Link2 aria-hidden className="h-4 w-4" /> Customer 360
          </Link>
        </div>

        <div className="flex flex-wrap gap-1.5" aria-label="Case labels">
          <Badge tone={card.stage === "completed" ? "success" : card.stage === "not_required" ? "danger" : "info"}>{REACTIVATION_STAGE_LABELS[card.stage]}</Badge>
          {card.labels.map((label) => <Badge key={label} tone={label === "priority" ? "danger" : "neutral"}>{REACTIVATION_LABEL_NAMES[label]}</Badge>)}
        </div>

        <div role="tablist" aria-label="Reactivation case details" className="grid grid-cols-5 gap-1 rounded-xl border border-border bg-surface-2 p-1">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`flex min-h-11 items-center justify-center gap-1.5 rounded-lg px-2 text-xs font-semibold ${tab === key ? "bg-surface text-accent shadow-sm" : "text-text-secondary hover:text-text-primary"}`}
            >
              <Icon aria-hidden className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {tab === "overview" ? (
          <div role="tabpanel" className="space-y-4">
            <CaseFacts card={card} />

            <section className="rounded-xl border border-border p-4">
              <div className="flex items-center gap-2">
                <UserRound aria-hidden className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold text-text-primary">Status, ownership and reminders</h3>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="text-xs font-medium text-text-secondary sm:col-span-2">
                  Primary status
                  <select aria-label="Primary case status" value={card.stage} onChange={(event) => onMove(card, event.target.value as ReactivationStage)} disabled={!canTransition || card.available_transitions.length === 0} className={`${FIELD} mt-1 disabled:opacity-60`}>
                    <option value={card.stage}>{REACTIVATION_STAGE_LABELS[card.stage]}</option>
                    {REACTIVATION_STAGES.filter((stage) => card.available_transitions.includes(stage)).map((stage) => <option key={stage} value={stage}>{REACTIVATION_STAGE_LABELS[stage]}</option>)}
                  </select>
                </label>
                <label className="text-xs font-medium text-text-secondary sm:col-span-2">
                  Assigned owner
                  <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} disabled={!canWrite} className={`${FIELD} mt-1 disabled:opacity-60`}>
                    <option value="">Unassigned</option>
                    {assignees.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
                  </select>
                </label>
                <fieldset className="sm:col-span-2">
                  <legend className="text-xs font-medium text-text-secondary">Labels</legend>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {REACTIVATION_LABELS.map((label) => <button key={label} type="button" aria-pressed={labels.includes(label)} disabled={!canWrite} onClick={() => toggleLabel(label)} className={`min-h-9 rounded-full border px-3 text-xs font-semibold transition ${labels.includes(label) ? "border-accent bg-accent-soft text-accent" : "border-border bg-surface text-text-secondary hover:bg-hover"} disabled:opacity-60`}>{REACTIVATION_LABEL_NAMES[label]}</button>)}
                  </div>
                </fieldset>
                {labels.includes("follow_up") ? <label className="text-xs font-medium text-text-secondary">Next follow-up date<span className="text-danger"> *</span><input aria-label="Next follow-up date" type="datetime-local" value={followUpAt} onChange={(event) => setFollowUpAt(event.target.value)} disabled={!canWrite} className={`${FIELD} mt-1 disabled:opacity-60`} /></label> : null}
                {labels.includes("name_change") ? <label className="text-xs font-medium text-text-secondary">Release date<span className="text-danger"> *</span><input aria-label="Release date" type="datetime-local" value={releaseAt} onChange={(event) => setReleaseAt(event.target.value)} disabled={!canWrite} className={`${FIELD} mt-1 disabled:opacity-60`} /></label> : null}
                <label className="text-xs font-medium text-text-secondary">
                  Previous Vi number
                  <input value={previousNumber} onChange={(event) => setPreviousNumber(event.target.value)} disabled={!canWrite} className={`${FIELD} mt-1 disabled:opacity-60`} />
                </label>
                <label className="text-xs font-medium text-text-secondary">
                  Active Delhi number
                  <input value={activeNumber} onChange={(event) => setActiveNumber(event.target.value)} disabled={!canWrite} className={`${FIELD} mt-1 disabled:opacity-60`} />
                </label>
              </div>
              {update.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(update.error)} /></div> : null}
              {labels.some((label) => label === "follow_up" || label === "name_change") && !ownerId ? <p className="mt-3 text-xs text-warning">Assign a staff member before scheduling a reminder.</p> : null}
              {canWrite ? <div className="mt-3 flex justify-end"><Button size="sm" onClick={saveOwnership} disabled={update.isPending || missingRequiredDate || (labels.some((label) => label === "follow_up" || label === "name_change") && !ownerId)}>{update.isPending ? "Saving…" : "Save case"}</Button></div> : null}
            </section>

            {card.reminders.length > 0 ? <section aria-label="Scheduled reminders" className="rounded-xl border border-border p-4"><div className="flex items-center gap-2"><CalendarClock aria-hidden className="h-4 w-4 text-accent" /><h3 className="text-sm font-semibold text-text-primary">Scheduled reminders</h3></div><div className="mt-3 space-y-2">{card.reminders.map((task) => <div key={task.id} className="flex flex-col gap-3 rounded-lg bg-surface-2 p-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-semibold text-text-primary">{task.title}</p><p className={`mt-1 text-xs ${new Date(task.due_at) < new Date() ? "text-danger" : "text-text-secondary"}`}>{new Date(task.due_at).toLocaleString()} · {task.assigned_agent_name ?? "Assigned staff"}</p></div><TaskActions task={task} showLinks={false} /></div>)}</div></section> : null}

            <EligibilityPanel card={card} />

            <section className="rounded-xl border border-border p-4">
              <h3 className="text-sm font-semibold text-text-primary">Permitted next actions</h3>
              <p className="mt-1 text-xs text-text-secondary">The server-owned transition matrix and domain gates remain authoritative.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {card.available_transitions.length === 0 ? <Badge tone="neutral">Terminal stage</Badge> : card.available_transitions.map((target) => (
                  <Button key={target} size="sm" variant="secondary" disabled={!canTransition} onClick={() => onMove(card, target)}>
                    Move to {REACTIVATION_STAGE_LABELS[target]}
                  </Button>
                ))}
              </div>
              {!canTransition ? <p className="mt-2 text-xs text-warning">Your role can review this case but cannot move it.</p> : null}
            </section>
          </div>
        ) : null}

        {tab === "activity" ? <CaseActivity card={card} /> : null}
        {tab === "work" ? <div role="tabpanel"><TasksSectionForProfile contactId={card.contact_id} /></div> : null}
        {tab === "documents" ? <div role="tabpanel"><DocumentWorkspace contactId={card.contact_id} compact /></div> : null}
        {tab === "kyc" ? <KycEntryPanel card={card} /> : null}
      </div>
    </Modal>
  );
}

function KycEntryPanel({ card }: { card: ReactivationCard }): JSX.Element {
  const canRead = useHasPermission("kyc:read");
  const canWrite = useHasPermission("kyc:write");
  const query = useContactKycCases(card.contact_id, canRead);
  const create = useCreateKycCase();
  const record = query.data?.[0];
  const eligibleStage = ["documents_received", "kyc_verification"].includes(card.stage);
  if (!canRead) return <EmptyState title="KYC access is restricted" description="Your role cannot view this case's KYC record." />;
  if (query.isLoading) return <Skeleton className="h-36 w-full" />;
  if (query.isError) return <ErrorState message={kycErrorMessage(query.error)} onRetry={() => void query.refetch()} />;
  if (record) return <section role="tabpanel" className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-text-primary">Governed KYC case</h3><p className="mt-1 text-xs text-text-secondary">Verification state is persisted and shared with Customer 360.</p></div><Badge tone={record.status === "approved" ? "success" : record.status === "rejected" ? "danger" : "warning"}>{KYC_STATUS_LABELS[record.status]}</Badge></div><div className="mt-3 grid grid-cols-3 gap-2">{[["Holder",record.holder_verified],["Delhi",record.delhi_presence_verified],["Active number",record.active_delhi_number_verified]].map(([label,value]) => <div key={label as string} className="rounded-lg bg-surface-2 p-2 text-center"><p className="text-[10px] font-semibold uppercase tracking-wide text-text-disabled">{label as string}</p><p className={`mt-1 text-xs font-semibold ${value ? "text-success" : "text-warning"}`}>{value ? "Verified" : "Required"}</p></div>)}</div><Link to="/reactivation/kyc" className="mt-4 inline-flex"><Button>Open KYC Operations</Button></Link></section>;
  return <section role="tabpanel" className="rounded-xl border border-border p-4"><div className="flex items-center gap-2"><ShieldAlert aria-hidden className="h-4 w-4 text-accent" /><h3 className="text-sm font-semibold text-text-primary">Open KYC case</h3></div><p className="mt-2 text-xs leading-relaxed text-text-secondary">KYC can begin only after governed documents are received. Opening the case records audit and Timeline evidence; manager approval governs the KYC / Verification hand-off.</p>{!eligibleStage ? <div className="mt-3"><EmptyState compact title="KYC prerequisites are not met" description={`Move the case through governed document intake before KYC. Current status: ${REACTIVATION_STAGE_LABELS[card.stage]}.`} /></div> : null}{create.error ? <div className="mt-3"><ErrorState message={kycErrorMessage(create.error)} /></div> : null}{canWrite && eligibleStage ? <div className="mt-4 flex justify-end"><Button loading={create.isPending} onClick={() => create.mutate({ caseId: card.id, ownerUserId: card.owner_user_id })}>Create KYC case</Button></div> : !canWrite ? <p className="mt-3 text-xs text-warning">Read-only: KYC write permission is required.</p> : null}</section>;
}

function CaseFacts({ card }: { card: ReactivationCard }): JSX.Element {
  const family = card.family_plan_required === null ? "Not recorded" : card.family_plan_required ? "Required" : "Not required";
  const conversion = card.conversion_indicator === "converted" ? "Converted" : card.conversion_indicator === "lost" ? "Closed without conversion" : "In progress";
  const facts = [
    ["Eligibility", card.latest_eligibility_status?.replaceAll("_", " ") ?? "Not checked"],
    ["Reservation", card.reservation_status ?? "Not recorded"],
    ["Family plan", family],
    ["Conversion", conversion],
    ["Documents", `${card.verified_document_count}/${card.document_count} verified`],
    ["SLA", card.sla_status.replaceAll("_", " ")],
  ];
  return (
    <section aria-label="Persisted case facts" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {facts.map(([label, value]) => <div key={label} className="rounded-xl border border-border bg-surface-2 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-text-disabled">{label}</p><p className="mt-1 text-sm font-semibold capitalize text-text-primary">{value}</p></div>)}
      {card.family_numbers.length > 0 ? <div className="rounded-xl border border-border bg-surface-2 p-3 sm:col-span-2 lg:col-span-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-text-disabled">Related family numbers</p><p className="mt-1 text-sm text-text-primary">{card.family_numbers.join(", ")}</p></div> : null}
      {card.closed_reason || card.latest_eligibility_reason ? <div className="rounded-xl border border-danger/30 bg-danger/5 p-3 sm:col-span-2 lg:col-span-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-danger">Rejection or closure evidence</p><p className="mt-1 text-sm text-text-primary">{card.closed_reason ?? card.latest_eligibility_reason}</p></div> : null}
    </section>
  );
}

function EligibilityPanel({ card }: { card: ReactivationCard }): JSX.Element {
  const checks = useEligibilityChecks(card.id);
  const record = useRecordEligibility(card.id);
  const canTransition = useHasPermission("reactivation:transition");
  const [status, setStatus] = useState<"eligible" | "not_eligible" | "review_required">("eligible");
  const [reason, setReason] = useState("");
  const canRecord = canTransition && card.stage === "lead_confirmed";

  return (
    <section className="rounded-xl border border-border p-4">
      <div className="flex items-center justify-between gap-2"><div><h3 className="text-sm font-semibold text-text-primary">Eligibility evidence</h3><p className="mt-1 text-xs text-text-secondary">Immutable decisions and rejection reasons.</p></div><Badge tone={card.latest_eligibility_status === "eligible" ? "success" : card.latest_eligibility_status === "not_eligible" ? "danger" : "neutral"}>{card.latest_eligibility_status?.replaceAll("_", " ") ?? "Not checked"}</Badge></div>
      {checks.isLoading ? <Skeleton className="mt-3 h-12 w-full" /> : checks.isError ? <div className="mt-3"><ErrorState message={apiErrorMessage(checks.error)} onRetry={() => void checks.refetch()} /></div> : (checks.data ?? []).length > 0 ? <ol className="mt-3 space-y-2">{(checks.data ?? []).slice().reverse().map((check) => <li key={check.id} className="rounded-lg bg-surface-2 p-2 text-xs"><span className="font-semibold capitalize text-text-primary">{check.status.replaceAll("_", " ")}</span><span className="text-text-secondary"> · {check.source} · {new Date(check.checked_at).toLocaleString()}</span>{check.reason ? <p className="mt-1 text-text-secondary">{check.reason}</p> : null}</li>)}</ol> : <div className="mt-3"><EmptyState compact title="No eligibility decision" description="Record a decision while the case is in Eligibility check." /></div>}
      {canRecord ? <div className="mt-3 grid gap-2 sm:grid-cols-[12rem_1fr_auto]"><select aria-label="Eligibility decision" value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className={FIELD}><option value="eligible">Eligible</option><option value="not_eligible">Not eligible</option><option value="review_required">Review required</option></select><input aria-label="Eligibility reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder={status === "not_eligible" ? "Rejection reason (required)" : "Decision note (optional)"} className={FIELD} /><Button size="sm" disabled={record.isPending || (status === "not_eligible" && !reason.trim())} onClick={() => record.mutate({ status, reason }, { onSuccess: () => setReason("") })}>Record</Button></div> : null}
      {record.error ? <p className="mt-2 text-xs text-danger">{apiErrorMessage(record.error)}</p> : null}
    </section>
  );
}

function CaseActivity({ card }: { card: ReactivationCard }): JSX.Element {
  const events = useReactivationEvents(card.id);
  const notes = useReactivationNotes(card.id);
  const addNote = useAddReactivationNote(card.id);
  const canWrite = useHasPermission("reactivation:write");
  const [body, setBody] = useState("");

  return (
    <div role="tabpanel" className="space-y-4">
      <section className="rounded-xl border border-border p-4">
        <div className="flex items-center gap-2"><History aria-hidden className="h-4 w-4 text-accent" /><h3 className="text-sm font-semibold text-text-primary">Immutable stage history</h3></div>
        {events.isLoading ? <div className="mt-3 space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div> : events.isError ? <div className="mt-3"><ErrorState message={apiErrorMessage(events.error)} onRetry={() => void events.refetch()} /></div> : (events.data ?? []).length === 0 ? <div className="mt-3"><EmptyState compact title="No stage history" /></div> : <ol className="mt-3 border-l border-border pl-4">{(events.data ?? []).slice().reverse().map((event) => <li key={event.id} className="relative pb-4 last:pb-0"><span aria-hidden className="absolute -left-[1.22rem] top-1.5 h-2 w-2 rounded-full bg-accent" /><p className="text-sm font-semibold text-text-primary">{event.from_stage ? `${REACTIVATION_STAGE_LABELS[event.from_stage]} → ` : "Created in "}{REACTIVATION_STAGE_LABELS[event.to_stage]}</p><p className="mt-0.5 text-xs text-text-secondary">{new Date(event.created_at).toLocaleString()}</p>{event.reason ? <p className="mt-1 text-xs text-text-secondary">{event.reason}</p> : null}</li>)}</ol>}
      </section>

      <section className="rounded-xl border border-border p-4">
        <div className="flex items-center gap-2"><MessageSquareText aria-hidden className="h-4 w-4 text-accent" /><h3 className="text-sm font-semibold text-text-primary">Internal case notes</h3></div>
        {notes.isLoading ? <Skeleton className="mt-3 h-16 w-full" /> : notes.isError ? <div className="mt-3"><ErrorState message={apiErrorMessage(notes.error)} onRetry={() => void notes.refetch()} /></div> : (notes.data ?? []).length === 0 ? <div className="mt-3"><EmptyState compact title="No case notes" description="Notes stay internal and are projected to the Customer Timeline." /></div> : <ul className="mt-3 space-y-2">{(notes.data ?? []).map((note) => <li key={note.id} className="rounded-lg border border-border bg-surface-2 p-3"><p className="whitespace-pre-wrap text-sm text-text-primary">{note.body}</p><p className="mt-1 text-[11px] text-text-secondary">{new Date(note.created_at).toLocaleString()} · actor {note.actor_user_id.slice(0, 8)}</p></li>)}</ul>}
        {canWrite ? <div className="mt-3"><label htmlFor="reactivation-note" className="sr-only">Add an internal case note</label><textarea id="reactivation-note" value={body} onChange={(event) => setBody(event.target.value)} rows={3} maxLength={4096} placeholder="Add an internal note for the reactivation team" className={`${FIELD} h-auto py-2`} /><div className="mt-2 flex items-center justify-between gap-2"><span className="text-[11px] text-text-disabled">{body.length}/4096 · saved to audit and Customer Timeline</span><Button size="sm" disabled={!body.trim() || addNote.isPending} onClick={() => addNote.mutate(body.trim(), { onSuccess: () => setBody("") })}>{addNote.isPending ? "Saving…" : "Add note"}</Button></div>{addNote.error ? <p className="mt-2 text-xs text-danger">{apiErrorMessage(addNote.error)}</p> : null}</div> : null}
      </section>

      <section className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-xl border border-border p-3"><div className="flex items-center gap-2"><CalendarClock aria-hidden className="h-4 w-4 text-accent" /><span className="text-xs font-semibold text-text-secondary">Stage entered</span></div><p className="mt-2 text-sm font-semibold text-text-primary">{new Date(card.stage_entered_at).toLocaleString()}</p></div>
        <div className="rounded-xl border border-border p-3"><div className="flex items-center gap-2">{card.sla_status === "breached" ? <ShieldAlert aria-hidden className="h-4 w-4 text-danger" /> : <CheckCircle2 aria-hidden className="h-4 w-4 text-success" />}<span className="text-xs font-semibold text-text-secondary">SLA evidence</span></div><p className="mt-2 text-sm font-semibold capitalize text-text-primary">{card.sla_status.replaceAll("_", " ")}</p>{card.sla_due_at ? <p className="mt-1 text-xs text-text-secondary">Due {new Date(card.sla_due_at).toLocaleString()}</p> : null}</div>
      </section>
    </div>
  );
}
