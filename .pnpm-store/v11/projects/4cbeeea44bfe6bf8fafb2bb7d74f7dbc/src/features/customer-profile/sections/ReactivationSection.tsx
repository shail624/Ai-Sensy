import {
  AlarmClock,
  ArrowUpRight,
  BadgeCheck,
  CalendarClock,
  History,
  PackageCheck,
  ShieldCheck,
  Smartphone,
  UserRoundCheck,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Section, Skeleton } from "@/components/ui";
import {
  apiErrorMessage,
  useCaseActivations,
  useCaseSimOrders,
  useContactReactivation,
} from "@/features/customer-profile/api";
import type { Contact } from "@/features/customer-profile/types";
import { useContactKycCases } from "@/features/kyc/api";
import { KYC_STATUS_LABELS } from "@/features/kyc/types";
import { useReactivationNotes } from "@/features/reactivation/api";
import {
  REACTIVATION_LABEL_NAMES,
  REACTIVATION_STAGE_LABELS,
} from "@/features/reactivation/types";
import { useHasPermission } from "@/lib/auth";

function statusTone(status: string): "neutral" | "success" | "warning" | "danger" | "accent" {
  if (["completed", "approved", "delivered"].includes(status)) return "success";
  if (["not_required", "rejected", "failed", "cancelled"].includes(status)) return "danger";
  if (["new_lead", "pending", "requested"].includes(status)) return "neutral";
  return "warning";
}

function titleCase(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Fact({ label, value }: { label: string; value: string | null | undefined }): JSX.Element {
  return <div className="rounded-xl border border-border bg-surface-2 px-3 py-2.5"><dt className="text-[11px] font-semibold uppercase tracking-wide text-text-disabled">{label}</dt><dd className="mt-1 break-words text-sm font-medium text-text-primary">{value || "Not recorded"}</dd></div>;
}

/** Factual read projection over the existing Reactivation, Task, KYC, SIM and Activation authorities. */
export function ReactivationSection({ contact }: { contact: Contact; focus?: "all" | "kyc" | "sim" }): JSX.Element {
  const navigate = useNavigate();
  const canRead = useHasPermission("reactivation:read");
  const canReadKyc = useHasPermission("kyc:read");
  const canReadSim = useHasPermission("sim:read");
  const canReadActivation = useHasPermission("activation:read");
  const reactivation = useContactReactivation(contact.id, canRead);
  const caseId = reactivation.data?.id ? String(reactivation.data.id) : "";
  const kyc = useContactKycCases(contact.id, canReadKyc);
  const simOrders = useCaseSimOrders(caseId, canReadSim && Boolean(caseId));
  const activations = useCaseActivations(caseId, canReadActivation && Boolean(caseId));
  const notes = useReactivationNotes(canRead && caseId ? caseId : "");

  if (!canRead) {
    return <Section title="Vi operations" description="Operational facts follow Reactivation permissions."><EmptyState compact title="Operations are restricted" description="Your role can view the customer identity but not the Reactivation case." /></Section>;
  }
  if (reactivation.isLoading) {
    return <div className="space-y-4"><Skeleton className="h-40 w-full" /><Skeleton className="h-56 w-full" /></div>;
  }
  if (reactivation.isError) {
    return <ErrorState message={apiErrorMessage(reactivation.error)} onRetry={() => void reactivation.refetch()} />;
  }
  const record = reactivation.data;
  if (!record) {
    return <Section title="Vi operations" description="No inferred status is created from contact attributes."><EmptyState compact title="No Reactivation case" description="This customer has no persisted Reactivation workflow yet." action={<Button variant="secondary" onClick={() => navigate("/reactivation/pipeline")}>Open Reactivation</Button>} /></Section>;
  }

  const latestKyc = kyc.data?.[0];
  const latestSim = simOrders.data?.[0];
  const latestActivation = activations.data?.[0];

  return (
    <div className="space-y-4">
      <Section
        title="Reactivation case"
        description="One server-owned customer case with status, labels, reminders, ownership and SLA evidence."
        icon={<BadgeCheck aria-hidden className="h-4 w-4" />}
        action={<Button variant="secondary" leftIcon={<ArrowUpRight aria-hidden className="h-4 w-4" />} onClick={() => navigate("/reactivation/pipeline")}>Open pipeline</Button>}
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={statusTone(record.stage)} dot>{REACTIVATION_STAGE_LABELS[record.stage]}</Badge>
          {record.labels.map((label) => <Badge key={label} tone={label === "priority" ? "danger" : "accent"}>{REACTIVATION_LABEL_NAMES[label]}</Badge>)}
          {record.labels.length === 0 ? <span className="text-xs text-text-disabled">No workflow labels</span> : null}
        </div>
        <dl className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <Fact label="Assigned staff" value={record.owner_name ?? (record.owner_user_id ? String(record.owner_user_id) : null)} />
          <Fact label="Previous Vi number" value={record.previous_vi_number} />
          <Fact label="Active Delhi number" value={record.active_delhi_number} />
          <Fact label="Source" value={record.source} />
          <Fact label="Reservation" value={record.reservation_status} />
          <Fact label="SLA" value={record.sla_status === "not_configured" ? "Not configured" : titleCase(record.sla_status)} />
          <Fact label="Family plan" value={record.family_plan_required === null ? null : record.family_plan_required ? "Required" : "Not required"} />
          <Fact label="Conversion" value={titleCase(record.conversion_indicator)} />
        </dl>
        {record.family_numbers.length ? <div className="mt-3 rounded-xl border border-border px-3 py-2"><p className="text-xs font-semibold text-text-secondary">Related family numbers</p><div className="mt-2 flex flex-wrap gap-2">{record.family_numbers.map((number) => <Badge key={number}>{number}</Badge>)}</div></div> : null}
      </Section>

      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Scheduled follow-ups" description="Open Task records remain the reminder authority." icon={<CalendarClock aria-hidden className="h-4 w-4" />}>
          {record.reminders.length === 0 ? <EmptyState compact title="No open reminder" description="Follow-up and Release dates appear here when their governed labels are active." /> : <ul className="space-y-2">{record.reminders.slice(0, 5).map((reminder) => <li key={reminder.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2.5"><div className="min-w-0"><p className="truncate text-sm font-medium text-text-primary">{reminder.title}</p><p className="mt-0.5 text-xs text-text-secondary">Due {new Date(reminder.due_at).toLocaleString()}</p></div><Badge tone={new Date(reminder.due_at) < new Date() ? "danger" : "warning"}><AlarmClock aria-hidden className="h-3 w-3" />{new Date(reminder.due_at) < new Date() ? "Overdue" : "Scheduled"}</Badge></li>)}</ul>}
        </Section>

        <Section title="Internal case notes" description="Immutable notes from the Reactivation Customer Timeline." icon={<History aria-hidden className="h-4 w-4" />}>
          {notes.isLoading ? <Skeleton className="h-24 w-full" /> : notes.isError ? <ErrorState message={apiErrorMessage(notes.error)} onRetry={() => void notes.refetch()} /> : (notes.data ?? []).length === 0 ? <EmptyState compact title="No case notes" description="Notes added from the case drawer appear here without a second notes store." /> : <ol className="space-y-2">{(notes.data ?? []).slice(0, 5).map((note) => <li key={note.id} className="rounded-xl border border-border bg-surface-2 px-3 py-2.5"><p className="text-sm leading-relaxed text-text-primary">{note.body}</p><time className="mt-1 block text-xs text-text-disabled">{new Date(note.created_at).toLocaleString()}</time></li>)}</ol>}
        </Section>
      </div>

      <section aria-labelledby="domain-facts-title" className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        <header className="border-b border-border px-4 py-3.5"><h3 id="domain-facts-title" className="text-sm font-semibold text-text-primary">Protected domain facts</h3><p className="mt-0.5 text-xs text-text-secondary">Read-only projections; operational changes stay in their governed source workflows.</p></header>
        <div className="grid divide-y divide-border md:grid-cols-3 md:divide-x md:divide-y-0">
          <div className="p-4">
            <div className="flex items-center justify-between gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent"><ShieldCheck aria-hidden className="h-4 w-4" /></span>{latestKyc ? <Badge tone={statusTone(latestKyc.status)}>{KYC_STATUS_LABELS[latestKyc.status]}</Badge> : null}</div>
            <h4 className="mt-3 text-sm font-semibold text-text-primary">KYC verification</h4>
            {!canReadKyc ? <p className="mt-2 text-xs text-text-secondary">Restricted by KYC permissions.</p> : kyc.isLoading ? <Skeleton className="mt-2 h-10 w-full" /> : kyc.isError ? <p className="mt-2 text-xs text-danger">KYC facts could not be loaded.</p> : latestKyc ? <div className="mt-2 space-y-1 text-xs text-text-secondary"><p><UserRoundCheck aria-hidden className="mr-1 inline h-3.5 w-3.5" />Holder {latestKyc.holder_verified ? "verified" : "pending"}</p><p>Delhi presence {latestKyc.delhi_presence_verified ? "verified" : "pending"}</p><p>Active number {latestKyc.active_delhi_number_verified ? "verified" : "pending"}</p></div> : <p className="mt-2 text-xs text-text-secondary">No KYC case.</p>}
            {canReadKyc ? <Button className="mt-3" variant="secondary" onClick={() => navigate("/reactivation/kyc")}>Open KYC</Button> : null}
          </div>
          <div className="p-4">
            <div className="flex items-center justify-between gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent"><PackageCheck aria-hidden className="h-4 w-4" /></span>{latestSim ? <Badge tone={statusTone(latestSim.status)}>{titleCase(latestSim.status)}</Badge> : null}</div>
            <h4 className="mt-3 text-sm font-semibold text-text-primary">SIM fact</h4>
            {!canReadSim ? <p className="mt-2 text-xs text-text-secondary">Restricted by SIM permissions.</p> : simOrders.isLoading ? <Skeleton className="mt-2 h-10 w-full" /> : simOrders.isError ? <p className="mt-2 text-xs text-danger">SIM facts could not be loaded.</p> : latestSim ? <div className="mt-2 space-y-1 text-xs text-text-secondary"><p>{latestSim.service_area}</p><p>{latestSim.customer_confirmed ? "Customer confirmed" : "Customer confirmation pending"}</p><p>{latestSim.delivered_at ? `Delivered ${new Date(latestSim.delivered_at).toLocaleDateString()}` : "Delivery not recorded"}</p></div> : <p className="mt-2 text-xs text-text-secondary">No SIM order; current need remains visible in the case status.</p>}
          </div>
          <div className="p-4">
            <div className="flex items-center justify-between gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent"><Smartphone aria-hidden className="h-4 w-4" /></span>{latestActivation ? <Badge tone={statusTone(latestActivation.status)}>{titleCase(latestActivation.status)}</Badge> : null}</div>
            <h4 className="mt-3 text-sm font-semibold text-text-primary">Activation fact</h4>
            {!canReadActivation ? <p className="mt-2 text-xs text-text-secondary">Restricted by Activation permissions.</p> : activations.isLoading ? <Skeleton className="mt-2 h-10 w-full" /> : activations.isError ? <p className="mt-2 text-xs text-danger">Activation facts could not be loaded.</p> : latestActivation ? <div className="mt-2 space-y-1 text-xs text-text-secondary"><p>{latestActivation.approved_at ? `Approved ${new Date(latestActivation.approved_at).toLocaleDateString()}` : "Approval not recorded"}</p><p>{latestActivation.completed_at ? `Completed ${new Date(latestActivation.completed_at).toLocaleDateString()}` : "Completion not recorded"}</p><p>{latestActivation.rejection_reason ?? "No rejection reason"}</p></div> : <p className="mt-2 text-xs text-text-secondary">No Activation record; current need remains visible in the case status.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
