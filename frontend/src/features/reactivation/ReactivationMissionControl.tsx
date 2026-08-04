import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  FileWarning,
  PackageCheck,
  RefreshCw,
  Rocket,
  ShieldCheck,
  UserRoundX,
  UsersRound,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import type { BadgeTone } from "@/components/ui/Badge";
import type { LucideIcon } from "lucide-react";
import { apiErrorMessage as kycErrorMessage, useKycOperations } from "@/features/kyc/api";
import {
  blockerReasons,
  buildMissionSnapshot,
  type AttentionSeverity,
  type ReactivationAttentionSignal,
  type ReactivationOperationalView,
} from "@/features/reactivation/missionControl";
import { apiErrorMessage, useReactivationPipeline } from "@/features/reactivation/api";
import { REACTIVATION_STAGE_LABELS } from "@/features/reactivation/types";
import { useHasPermission } from "@/lib/auth";

export function ReactivationMissionControl(): JSX.Element {
  const canReadKyc = useHasPermission("kyc:read");
  const pipeline = useReactivationPipeline({ limit: 200 });
  const kyc = useKycOperations({ limit: 200 }, canReadKyc);
  const cards = useMemo(() => pipeline.data?.data ?? [], [pipeline.data?.data]);
  const kycRows = useMemo(() => kyc.data?.data ?? [], [kyc.data?.data]);
  const snapshot = useMemo(() => buildMissionSnapshot(cards, kycRows), [cards, kycRows]);

  if (pipeline.isLoading) return <MissionControlLoading />;
  if (pipeline.isError) {
    return <ErrorState message={apiErrorMessage(pipeline.error)} onRetry={() => void pipeline.refetch()} />;
  }

  return (
    <div className="space-y-5">
      <section
        aria-labelledby="mission-attention-title"
        className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(19rem,0.75fr)]"
      >
        <Card className="overflow-hidden" padding={false}>
          <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5">
            <div>
              <div className="flex items-center gap-2">
                <AlertOctagon aria-hidden className="h-5 w-5 text-danger" />
                <h2 id="mission-attention-title" className="text-base font-semibold text-text-primary">
                  Attention now
                </h2>
                <Badge tone={snapshot.attention > 0 ? "danger" : "success"}>{snapshot.attention}</Badge>
              </div>
              <p className="mt-1 max-w-2xl text-xs leading-relaxed text-text-secondary">
                Ranked from the currently loaded tenant-scoped set by persisted SLA, overdue work,
                release-date risk, evidence gaps, ownership and business labels.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              loading={pipeline.isFetching || (canReadKyc && kyc.isFetching)}
              leftIcon={<RefreshCw aria-hidden className="h-4 w-4" />}
              onClick={() => {
                void pipeline.refetch();
                if (canReadKyc) void kyc.refetch();
              }}
            >
              Refresh
            </Button>
          </div>

          {snapshot.topAttention.length === 0 ? (
            <div className="p-7">
              <EmptyState
                icon={<CheckCircle2 className="h-7 w-7" />}
                title="No urgent case in the loaded operating set"
                description="Open the full pipeline to review routine work, upcoming reminders and completed cases."
                action={<MissionLink to="/reactivation/pipeline?view=all" label="Open full pipeline" />}
              />
            </div>
          ) : (
            <>
              <AttentionTable rows={snapshot.topAttention} />
              <div className="border-t border-border px-4 py-3 sm:px-5">
                <MissionLink to="/reactivation/pipeline?view=attention" label="Open prioritized queue" />
              </div>
            </>
          )}
        </Card>

        <Card className="p-4 sm:p-5" padding={false}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Loaded operating set</p>
              <p className="mt-1 text-3xl font-bold text-text-primary">{snapshot.active}</p>
              <p className="mt-1 text-xs text-text-secondary">
                Active cases · {pipeline.data?.total ?? cards.length} total source records
              </p>
            </div>
            <span className="flex h-11 w-11 items-center justify-center rounded-control bg-accent-soft text-accent">
              <UsersRound aria-hidden className="h-5 w-5" />
            </span>
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border pt-4 text-xs">
            <MissionFact label="Blocked" value={snapshot.blocked} tone={snapshot.blocked > 0 ? "danger" : "neutral"} />
            <MissionFact label="Unassigned" value={snapshot.unassigned} tone={snapshot.unassigned > 0 ? "warning" : "neutral"} />
            <MissionFact label="Completed" value={snapshot.completed} tone="success" />
            <MissionFact label="KYC loaded" value={canReadKyc ? kycRows.length : "Restricted"} />
          </dl>
          <p className="mt-4 rounded-control border border-border bg-surface-2 p-3 text-[11px] leading-relaxed text-text-secondary">
            Counts reflect bounded source reads. Pipeline and KYC queues remain authoritative for
            complete pagination and object-level decisions.
          </p>
          {canReadKyc && kyc.isError ? (
            <div role="status" className="mt-3 rounded-control border border-warning/40 bg-warning/10 p-3 text-xs text-warning">
              KYC signals are temporarily unavailable: {kycErrorMessage(kyc.error)}
            </div>
          ) : null}
        </Card>
      </section>

      <section aria-labelledby="operating-queues-title">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 id="operating-queues-title" className="text-base font-semibold text-text-primary">Operating queues</h2>
            <p className="mt-1 text-xs text-text-secondary">One click opens the exact working context instead of a generic module home.</p>
          </div>
          <Link to="/reactivation/pipeline?view=all" className="hidden text-xs font-semibold text-accent hover:underline sm:inline">View all cases</Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <QueueLink icon={AlertTriangle} label="Overdue and SLA" value={snapshot.overdue} detail="Follow-ups, tasks or SLA already breached" view="overdue" tone="danger" />
          <QueueLink icon={CalendarClock} label="Release-date risk" value={snapshot.releaseRisk} detail="Name-change release due within three days" view="release" tone="warning" />
          <QueueLink icon={FileWarning} label="Document gaps" value={snapshot.documentGaps} detail="Missing or unverified customer evidence" view="documents" tone="warning" />
          <QueueLink icon={ClipboardCheck} label="Pending KYC" value={snapshot.pendingKyc} detail={snapshot.missingKycEvidence > 0 ? `${snapshot.missingKycEvidence} KYC records lack complete evidence` : "Awaiting governed review or decision"} to="/reactivation/kyc" tone="info" />
          <QueueLink icon={PackageCheck} label="SIM fulfilment risk" value={snapshot.simRisk} detail="SIM-required cases with urgency signals" view="sim" tone="info" />
          <QueueLink icon={Rocket} label="Activation risk" value={snapshot.activationRisk} detail="Activation hand-offs needing attention" view="activation" tone="danger" />
          <QueueLink icon={UserRoundX} label="Unassigned active" value={snapshot.unassigned} detail="Cases without an accountable operator" view="unassigned" tone="warning" />
          <QueueLink icon={ShieldCheck} label="Priority cases" value={cards.filter((card) => card.labels.includes("priority")).length} detail="Business-priority work marked by operators" view="priority" tone="info" />
        </div>
      </section>

      <section aria-labelledby="live-workspaces-title" className="rounded-surface border border-border bg-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 id="live-workspaces-title" className="text-sm font-semibold text-text-primary">Live operational workspaces</h2>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-text-secondary">
              These destinations are backed by persisted records and existing permission, audit and
              transition authorities. Foundation-only routes are separated from this operating path.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <MissionLink to="/reactivation/pipeline?view=attention" label="Customer pipeline" />
            {canReadKyc ? <MissionLink to="/reactivation/kyc" label="KYC operations" secondary /> : null}
            <MissionLink to="/reactivation/documents" label="Document Center" secondary />
            <MissionLink to="/reactivation/reports" label="Reports" secondary />
          </div>
        </div>
      </section>
    </div>
  );
}

function AttentionTable({ rows }: { rows: ReactivationAttentionSignal[] }): JSX.Element {
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[850px] border-collapse text-left text-sm">
          <thead className="bg-surface-2 text-[11px] font-semibold uppercase tracking-wide text-text-disabled">
            <tr>
              <th className="px-5 py-3">Customer</th>
              <th className="px-4 py-3">Why now</th>
              <th className="px-4 py-3">Next required action</th>
              <th className="px-4 py-3">Owner</th>
              <th className="w-12 px-4 py-3"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((signal) => (
              <tr key={signal.card.id} className="bg-surface transition-colors hover:bg-hover">
                <td className="px-5 py-3.5">
                  <p className="font-semibold text-text-primary">{signal.card.contact_name}</p>
                  <p className="mt-0.5 text-xs text-text-secondary">{REACTIVATION_STAGE_LABELS[signal.card.stage]} · {signal.card.contact_phone}</p>
                </td>
                <td className="px-4 py-3.5"><ReasonBadges signal={signal} /></td>
                <td className="max-w-xs px-4 py-3.5 text-xs leading-relaxed text-text-primary">{signal.nextAction}</td>
                <td className="px-4 py-3.5 text-xs text-text-secondary">{signal.card.owner_name ?? "Unassigned"}</td>
                <td className="px-4 py-3.5">
                  <Link
                    to={`/reactivation/pipeline?view=attention&case=${encodeURIComponent(signal.card.id)}`}
                    aria-label={`Open ${signal.card.contact_name}`}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-control border border-border text-accent transition-colors hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    <ArrowRight aria-hidden className="h-4 w-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="divide-y divide-border md:hidden">
        {rows.map((signal) => (
          <li key={signal.card.id}>
            <Link
              to={`/reactivation/pipeline?view=attention&case=${encodeURIComponent(signal.card.id)}`}
              className="block p-4 transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-text-primary">{signal.card.contact_name}</p>
                  <p className="mt-0.5 text-xs text-text-secondary">{REACTIVATION_STAGE_LABELS[signal.card.stage]} · {signal.card.owner_name ?? "Unassigned"}</p>
                </div>
                <SeverityBadge severity={signal.severity} />
              </div>
              <div className="mt-3"><ReasonBadges signal={signal} /></div>
              <p className="mt-3 border-t border-border pt-3 text-xs font-medium leading-relaxed text-text-primary">{signal.nextAction}</p>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function ReasonBadges({ signal }: { signal: ReactivationAttentionSignal }): JSX.Element {
  const reasons = signal.reasons.length > 0 ? signal.reasons.slice(0, 2) : ["Operational priority"];
  return <div className="flex max-w-sm flex-wrap gap-1.5"><SeverityBadge severity={signal.severity} />{reasons.map((reason) => <Badge key={reason} tone="neutral">{reason}</Badge>)}</div>;
}

function SeverityBadge({ severity }: { severity: AttentionSeverity }): JSX.Element {
  const tone: BadgeTone = severity === "critical" ? "danger" : severity === "high" ? "warning" : severity === "medium" ? "info" : "neutral";
  return <Badge tone={tone}>{severity}</Badge>;
}

function QueueLink({
  icon: Icon,
  label,
  value,
  detail,
  view,
  to,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  detail: string;
  view?: ReactivationOperationalView;
  to?: string;
  tone: "danger" | "warning" | "info";
}): JSX.Element {
  const href = to ?? `/reactivation/pipeline?view=${view ?? "all"}`;
  const iconClass = tone === "danger" ? "bg-danger/10 text-danger" : tone === "warning" ? "bg-warning/10 text-warning" : "bg-accent-soft text-accent";
  return (
    <Link
      to={href}
      className="group flex min-h-28 items-start gap-3 rounded-surface border border-border bg-surface p-4 shadow-sm transition-[border-color,box-shadow] hover:border-border-strong hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
    >
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-control ${iconClass}`}><Icon aria-hidden className="h-5 w-5" /></span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-text-primary">{label}</span><span className="text-xl font-bold text-text-primary">{value}</span></span>
        <span className="mt-1 block text-xs leading-relaxed text-text-secondary">{detail}</span>
        <span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-accent">Open queue <ArrowRight aria-hidden className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" /></span>
      </span>
    </Link>
  );
}

function MissionFact({ label, value, tone = "neutral" }: { label: string; value: number | string; tone?: "neutral" | "success" | "warning" | "danger" }): JSX.Element {
  const valueClass = tone === "success" ? "text-success" : tone === "warning" ? "text-warning" : tone === "danger" ? "text-danger" : "text-text-primary";
  return <div><dt className="text-text-disabled">{label}</dt><dd className={`mt-0.5 text-base font-bold ${valueClass}`}>{value}</dd></div>;
}

function MissionLink({ to, label, secondary = false }: { to: string; label: string; secondary?: boolean }): JSX.Element {
  return (
    <Link
      to={to}
      className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-control border px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${secondary ? "border-border bg-surface text-text-primary hover:bg-hover" : "border-accent bg-accent text-accent-fg hover:bg-accent-hover"}`}
    >
      {label}<ArrowRight aria-hidden className="h-3.5 w-3.5" />
    </Link>
  );
}

function MissionControlLoading(): JSX.Element {
  return (
    <div aria-label="Loading Reactivation Mission Control" className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(19rem,0.75fr)]">
        <Skeleton className="h-[28rem] w-full" />
        <Skeleton className="h-[28rem] w-full" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }, (_, index) => <Skeleton key={index} className="h-28 w-full" />)}</div>
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

export function caseBlockerSummary(card: ReactivationAttentionSignal["card"]): string {
  return blockerReasons(card).join(" · ");
}
