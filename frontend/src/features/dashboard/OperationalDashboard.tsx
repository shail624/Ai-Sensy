import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BadgeAlert,
  BarChart3,
  BriefcaseBusiness,
  CheckCircle2,
  Clock3,
  FileWarning,
  MessageSquareReply,
  PackageCheck,
  RefreshCw,
  Send,
  ShieldAlert,
  Smartphone,
  UserRoundCog,
  UsersRound,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { useAnalyticsComparison } from "@/features/analytics/api";
import { FreshnessIndicator } from "@/features/analytics/FreshnessIndicator";
import type { AnalyticsFilterState } from "@/features/analytics/types";
import { useCampaigns } from "@/features/campaigns/api";
import {
  agentAttention,
  blockedReactivationCards,
  buildAttentionQueue,
  campaignsNeedingAction,
  conversationsNeedingReply,
  delayedSimCards,
  kpiChanges,
  overdueActivationCards,
  pendingKycReviews,
  reactivationReasons,
  templatesNeedingAction,
  type AgentAttentionRow,
  type AttentionItem,
  type AttentionSeverity,
} from "@/features/dashboard/selectors";
import { useConversations } from "@/features/inbox/api";
import { useKycOperations } from "@/features/kyc/api";
import { KYC_STATUS_LABELS } from "@/features/kyc/types";
import { useReactivationPipeline } from "@/features/reactivation/api";
import { REACTIVATION_STAGE_LABELS } from "@/features/reactivation/types";
import { useTaskStats, useTasks } from "@/features/tasks/api";
import { TaskActions } from "@/features/tasks/TaskActions";
import { TaskDue, TaskPriorityChip } from "@/features/tasks/TaskBadges";
import { useTemplates } from "@/features/templates/api";
import { apiErrorMessage } from "@/lib/api/errors";
import { useAuth, useHasPermission } from "@/lib/auth";

const TODAY_FILTERS: AnalyticsFilterState = {
  preset: "today",
  from: "",
  to: "",
  granularity: "hour",
  compare: "previous_period",
};

function severityTone(severity: AttentionSeverity): "danger" | "warning" | "info" {
  if (severity === "critical") return "danger";
  if (severity === "high") return "warning";
  return "info";
}

function SignalCell({
  icon: Icon,
  label,
  value,
  detail,
  href,
  loading = false,
  error = false,
  tone = "neutral",
}: {
  icon: typeof AlertTriangle;
  label: string;
  value?: number;
  detail: string;
  href: string;
  loading?: boolean;
  error?: boolean;
  tone?: "neutral" | "danger" | "warning" | "info";
}): JSX.Element {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "warning"
        ? "text-warning"
        : tone === "info"
          ? "text-info"
          : "text-accent";
  return (
    <Link
      to={href}
      className="group min-h-28 border-b border-border p-4 transition-colors hover:bg-hover focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus sm:border-r"
      aria-label={`${label}: ${error ? "unavailable" : loading ? "loading" : value ?? 0}. ${detail}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-control bg-surface-2 ${toneClass}`}>
          <Icon aria-hidden className="h-4.5 w-4.5" />
        </span>
        <ArrowRight aria-hidden className="h-4 w-4 text-text-disabled transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
      </div>
      <div className="mt-3">
        {loading ? (
          <Skeleton className="h-7 w-14" />
        ) : (
          <p className={`text-2xl font-bold tabular-nums ${error ? "text-text-disabled" : "text-text-primary"}`}>
            {error ? "—" : (value ?? 0).toLocaleString()}
          </p>
        )}
        <p className="mt-0.5 text-xs font-semibold text-text-primary">{label}</p>
        <p className="mt-1 text-[11px] leading-4 text-text-secondary">{error ? "Source unavailable — open the queue to retry." : detail}</p>
      </div>
    </Link>
  );
}

function MyTaskSignal(): JSX.Element {
  const stats = useTaskStats();
  return (
    <SignalCell
      icon={Clock3}
      label="My overdue tasks"
      value={stats.data?.overdue}
      detail="Assigned tasks that remain open past due"
      href="/tasks?view=overdue"
      loading={stats.isLoading}
      error={stats.isError}
      tone={(stats.data?.overdue ?? 0) > 0 ? "danger" : "neutral"}
    />
  );
}

function AttentionSummary({
  blocked,
  pendingKyc,
  delayedSim,
  overdueActivations,
  campaignActions,
  replies,
  templateActions,
  agents,
  queryState,
  permissions,
}: {
  blocked: number;
  pendingKyc: number;
  delayedSim: number;
  overdueActivations: number;
  campaignActions: number;
  replies: number;
  templateActions: number;
  agents: number;
  queryState: {
    reactivation: { loading: boolean; error: boolean };
    kyc: { loading: boolean; error: boolean };
    campaigns: { loading: boolean; error: boolean };
    inbox: { loading: boolean; error: boolean };
    templates: { loading: boolean; error: boolean };
  };
  permissions: {
    reactivation: boolean;
    kyc: boolean;
    campaigns: boolean;
    inbox: boolean;
    templates: boolean;
    tasks: boolean;
  };
}): JSX.Element {
  return (
    <section aria-labelledby="attention-summary-title" className="overflow-hidden rounded-surface border border-border bg-surface shadow-sm">
      <div className="border-b border-border px-4 py-3">
        <h2 id="attention-summary-title" className="text-sm font-semibold text-text-primary">Attention summary</h2>
        <p className="mt-0.5 text-xs text-text-secondary">Every count opens its governed source queue; unavailable sources are never shown as zero.</p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 [&>*:nth-last-child(-n+5)]:xl:border-b-0">
        {permissions.reactivation ? <SignalCell icon={ShieldAlert} label="Blocked customers" value={blocked} detail="SLA, overdue follow-up, missing documents or unreachable" href="/reactivation/pipeline" loading={queryState.reactivation.loading} error={queryState.reactivation.error} tone={blocked > 0 ? "danger" : "neutral"} /> : null}
        {permissions.kyc ? <SignalCell icon={FileWarning} label="KYC reviews pending" value={pendingKyc} detail="Cases currently awaiting reviewer action" href="/reactivation/kyc" loading={queryState.kyc.loading} error={queryState.kyc.error} tone={pendingKyc > 0 ? "warning" : "neutral"} /> : null}
        {permissions.reactivation ? <SignalCell icon={PackageCheck} label="SIM delivery risk" value={delayedSim} detail="SIM Required cases with breached SLA" href="/reactivation/pipeline" loading={queryState.reactivation.loading} error={queryState.reactivation.error} tone={delayedSim > 0 ? "danger" : "neutral"} /> : null}
        {permissions.reactivation ? <SignalCell icon={Smartphone} label="Activations overdue" value={overdueActivations} detail="Activation Pending cases with breached SLA" href="/reactivation/pipeline" loading={queryState.reactivation.loading} error={queryState.reactivation.error} tone={overdueActivations > 0 ? "danger" : "neutral"} /> : null}
        {permissions.campaigns ? <SignalCell icon={Send} label="Campaigns need action" value={campaignActions} detail="Failed, paused or carrying failed recipients" href="/campaigns" loading={queryState.campaigns.loading} error={queryState.campaigns.error} tone={campaignActions > 0 ? "warning" : "neutral"} /> : null}
        {permissions.inbox ? <SignalCell icon={MessageSquareReply} label="Replies waiting" value={replies} detail="Open or pending conversations with unread messages" href="/inbox" loading={queryState.inbox.loading} error={queryState.inbox.error} tone={replies > 0 ? "warning" : "neutral"} /> : null}
        {permissions.templates ? <SignalCell icon={BadgeAlert} label="Templates blocked" value={templateActions} detail="Rejected, paused or disabled by Meta" href="/templates" loading={queryState.templates.loading} error={queryState.templates.error} tone={templateActions > 0 ? "warning" : "neutral"} /> : null}
        {permissions.reactivation || permissions.kyc ? <SignalCell icon={UserRoundCog} label="Agents need attention" value={agents} detail="Owners with blocked, overdue, SLA or KYC work" href="/reactivation/pipeline" loading={queryState.reactivation.loading || queryState.kyc.loading} error={queryState.reactivation.error && queryState.kyc.error} tone={agents > 0 ? "info" : "neutral"} /> : null}
        {permissions.tasks ? <MyTaskSignal /> : null}
      </div>
    </section>
  );
}

function AttentionQueue({ items, loading, unavailable }: { items: AttentionItem[]; loading: boolean; unavailable: string[] }): JSX.Element {
  return (
    <Card padding={false} className="overflow-hidden">
      <div className="border-b border-border px-4 py-4 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-text-primary">What requires attention now?</h2>
            <p className="mt-1 text-xs text-text-secondary">Prioritized across customer, KYC, fulfilment, messaging and template sources.</p>
          </div>
          <Badge tone={items.some((item) => item.severity === "critical") ? "danger" : items.length > 0 ? "warning" : "success"} dot>
            {items.length > 0 ? `${items.length} visible actions` : "No visible action"}
          </Badge>
        </div>
        {unavailable.length > 0 ? (
          <div role="status" className="mt-3 flex items-start gap-2 rounded-control border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-warning-on-soft">
            <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
            <span><strong>Partial view.</strong> {unavailable.join(", ")} {unavailable.length === 1 ? "is" : "are"} unavailable; existing results remain actionable.</span>
          </div>
        ) : null}
      </div>
      {loading && items.length === 0 ? (
        <div aria-label="Loading operational attention" className="space-y-2 p-4">
          {Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-16 w-full" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="p-7">
          <EmptyState compact icon={<CheckCircle2 className="h-6 w-6" />} title={unavailable.length > 0 ? "No action found in the available sources" : "No immediate action is visible"} description={unavailable.length > 0 ? "Retry the unavailable sources before treating the queue as fully clear." : "The current authorized queues contain no blocked, overdue, failed or unread action items."} />
        </div>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-[11px] font-semibold uppercase tracking-wide text-text-disabled">
                <tr><th className="px-4 py-2.5">Priority</th><th className="px-4 py-2.5">Work item</th><th className="px-4 py-2.5">Owner</th><th className="px-4 py-2.5 text-right">Next step</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.slice(0, 10).map((item) => <AttentionRow key={item.id} item={item} />)}
              </tbody>
            </table>
          </div>
          <ul className="divide-y divide-border md:hidden">
            {items.slice(0, 10).map((item) => <AttentionCard key={item.id} item={item} />)}
          </ul>
          {items.length > 10 ? <p className="border-t border-border px-4 py-3 text-xs text-text-secondary">Showing the 10 highest-priority items from {items.length} visible actions.</p> : null}
        </>
      )}
    </Card>
  );
}

function AttentionRow({ item }: { item: AttentionItem }): JSX.Element {
  return (
    <tr className="hover:bg-hover">
      <td className="px-4 py-3"><div className="flex flex-wrap gap-1.5"><Badge tone={severityTone(item.severity)}>{item.severity}</Badge><Badge>{item.source}</Badge></div></td>
      <td className="max-w-xl px-4 py-3"><p className="font-semibold text-text-primary">{item.title}</p><p className="mt-0.5 text-xs leading-5 text-text-secondary">{item.detail}</p></td>
      <td className="px-4 py-3 text-xs font-medium text-text-secondary">{item.owner}</td>
      <td className="px-4 py-3 text-right"><Link to={item.href} className="inline-flex min-h-9 items-center gap-1.5 rounded-control px-2.5 text-xs font-semibold text-accent hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">{item.actionLabel}<ArrowRight aria-hidden className="h-3.5 w-3.5" /></Link></td>
    </tr>
  );
}

function AttentionCard({ item }: { item: AttentionItem }): JSX.Element {
  return (
    <li className="p-4">
      <div className="flex flex-wrap items-center gap-1.5"><Badge tone={severityTone(item.severity)}>{item.severity}</Badge><Badge>{item.source}</Badge></div>
      <p className="mt-2 text-sm font-semibold text-text-primary">{item.title}</p>
      <p className="mt-1 text-xs leading-5 text-text-secondary">{item.detail}</p>
      <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3"><span className="truncate text-xs text-text-secondary">{item.owner}</span><Link to={item.href} className="inline-flex min-h-9 shrink-0 items-center gap-1 text-xs font-semibold text-accent">{item.actionLabel}<ArrowRight aria-hidden className="h-3.5 w-3.5" /></Link></div>
    </li>
  );
}

function MyWorkSnapshot({ userId }: { userId: string | undefined }): JSX.Element {
  const stats = useTaskStats();
  const tasks = useTasks({ view: "overdue", assignee_id: userId, limit: 4 }, Boolean(userId));
  const rows = tasks.data?.data ?? [];
  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader
        className="border-b border-border px-4 py-4 sm:px-5"
        title="My work today"
        description="The signed-in operator’s open task authority"
        icon={<BriefcaseBusiness aria-hidden className="h-4 w-4" />}
        action={<Link to="/tasks" className="inline-flex min-h-9 items-center gap-1 rounded-control px-2 text-xs font-semibold text-accent hover:bg-accent-soft">View all<ArrowRight className="h-3.5 w-3.5" /></Link>}
      />
      <div className="grid grid-cols-3 divide-x divide-border border-b border-border bg-surface-2">
        <MiniMetric label="Overdue" value={stats.data?.overdue} loading={stats.isLoading} danger />
        <MiniMetric label="Due today" value={stats.data?.due_today} loading={stats.isLoading} />
        <MiniMetric label="Completed" value={stats.data?.completed_today} loading={stats.isLoading} success />
      </div>
      {stats.isError ? <div className="p-4"><ErrorState message={apiErrorMessage(stats.error)} onRetry={() => void stats.refetch()} /></div> : tasks.isLoading ? <div className="space-y-2 p-4">{Array.from({ length: 3 }, (_, index) => <Skeleton key={index} className="h-20 w-full" />)}</div> : tasks.isError ? <div className="p-4"><ErrorState message={apiErrorMessage(tasks.error)} onRetry={() => void tasks.refetch()} /></div> : rows.length === 0 ? <div className="p-5"><EmptyState compact title="No overdue task" description="Due-today and upcoming work remains available in Tasks." /></div> : <ul className="divide-y divide-border">{rows.map((task) => <li key={task.id} className="p-4"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-text-primary">{task.title}</p><p className="mt-0.5 truncate text-xs text-text-secondary">{task.contact_name ?? "No customer linked"}</p><div className="mt-2 flex flex-wrap items-center gap-1"><TaskPriorityChip value={task.priority} /><TaskDue task={task} /></div></div><TaskActions task={task} /></div></li>)}</ul>}
    </Card>
  );
}

function MiniMetric({ label, value, loading, danger = false, success = false }: { label: string; value?: number; loading: boolean; danger?: boolean; success?: boolean }): JSX.Element {
  return <div className="px-3 py-3 text-center">{loading ? <Skeleton className="mx-auto h-5 w-8" /> : <p className={`text-lg font-bold tabular-nums ${danger && (value ?? 0) > 0 ? "text-danger" : success ? "text-success" : "text-text-primary"}`}>{(value ?? 0).toLocaleString()}</p>}<p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-text-disabled">{label}</p></div>;
}

function BlockedCustomers({ cards, loading, error, onRetry }: { cards: ReturnType<typeof blockedReactivationCards>; loading: boolean; error: unknown; onRetry: () => void }): JSX.Element {
  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader className="border-b border-border px-4 py-4 sm:px-5" title="Blocked customers" description="The customer, blocker, owner and current stage in one view" icon={<UsersRound aria-hidden className="h-4 w-4" />} action={<Link to="/reactivation/pipeline" className="inline-flex min-h-9 items-center gap-1 rounded-control px-2 text-xs font-semibold text-accent hover:bg-accent-soft">Open pipeline<ArrowRight className="h-3.5 w-3.5" /></Link>} />
      {loading ? <div className="space-y-2 p-4">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-20 w-full" />)}</div> : error ? <div className="p-4"><ErrorState message={apiErrorMessage(error)} onRetry={onRetry} /></div> : cards.length === 0 ? <div className="p-5"><EmptyState compact title="No blocked customer is visible" description="No breached SLA, overdue follow-up, incomplete documents or unreachable-customer label is present." /></div> : <ul className="divide-y divide-border">{cards.slice(0, 6).map((card) => <li key={card.id} className="p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-text-primary">{card.contact_name}</p><p className="mt-0.5 text-xs text-text-secondary">{REACTIVATION_STAGE_LABELS[card.stage]} · {card.owner_name ?? "Unassigned"}</p></div>{card.sla_status === "breached" ? <Badge tone="danger">SLA breached</Badge> : <Badge tone="warning">Blocked</Badge>}</div><div className="mt-2 flex flex-wrap gap-1">{reactivationReasons(card).map((reason) => <Badge key={reason} tone={reason === "SLA breached" ? "danger" : "warning"}>{reason}</Badge>)}</div></li>)}</ul>}
    </Card>
  );
}

function AgentAttention({ rows, loading, errors }: { rows: AgentAttentionRow[]; loading: boolean; errors: boolean }): JSX.Element {
  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader className="border-b border-border px-4 py-4 sm:px-5" title="Agents requiring attention" description="Derived only from assigned blocked, overdue, SLA and KYC work" icon={<UserRoundCog aria-hidden className="h-4 w-4" />} action={<Link to="/reactivation/pipeline" className="inline-flex min-h-9 items-center gap-1 rounded-control px-2 text-xs font-semibold text-accent hover:bg-accent-soft">Review workload<ArrowRight className="h-3.5 w-3.5" /></Link>} />
      {loading ? <div className="space-y-2 p-4">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-14 w-full" />)}</div> : errors && rows.length === 0 ? <div className="p-5"><EmptyState compact title="Agent workload is partially unavailable" description="Both Reactivation and KYC sources must load before a clear result can be claimed." /></div> : rows.length === 0 ? <div className="p-5"><EmptyState compact title="No agent escalation is visible" description="The available assigned workload contains no blocker, overdue reminder, breached SLA or KYC review." /></div> : <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-xs"><thead className="border-b border-border bg-surface-2 text-[10px] font-semibold uppercase tracking-wide text-text-disabled"><tr><th className="px-4 py-2.5">Agent</th><th className="px-3 py-2.5 text-center">Blocked</th><th className="px-3 py-2.5 text-center">Overdue</th><th className="px-3 py-2.5 text-center">SLA</th><th className="px-3 py-2.5 text-center">KYC</th></tr></thead><tbody className="divide-y divide-border">{rows.slice(0, 6).map((row) => <tr key={row.name} className="hover:bg-hover"><td className="px-4 py-3 font-semibold text-text-primary">{row.name}{row.name === "Unassigned" ? <Badge className="ml-2" tone="danger">Assign now</Badge> : null}</td><td className="px-3 py-3 text-center tabular-nums text-text-secondary">{row.blockedCustomers}</td><td className="px-3 py-3 text-center tabular-nums text-text-secondary">{row.overdue}</td><td className="px-3 py-3 text-center tabular-nums text-text-secondary">{row.slaBreaches}</td><td className="px-3 py-3 text-center tabular-nums text-text-secondary">{row.kycReviews}</td></tr>)}</tbody></table></div>}
    </Card>
  );
}

function TodayKpis({ comparison, canAnalytics }: { comparison: ReturnType<typeof useAnalyticsComparison>; canAnalytics: boolean }): JSX.Element | null {
  if (!canAnalytics) return null;
  const rows = kpiChanges(comparison.data?.current.kpis, comparison.data?.previous_kpis);
  return (
    <Card padding={false} className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-4 py-4 sm:px-5">
        <div><div className="flex items-center gap-2"><BarChart3 aria-hidden className="h-4 w-4 text-accent" /><h2 className="text-base font-semibold text-text-primary">Which KPIs changed today?</h2></div><p className="mt-1 text-xs text-text-secondary">Today compared with the previous equivalent period; direction is interpreted per metric.</p></div>
        <div className="flex items-center gap-3"><FreshnessIndicator /><Link to="/analytics?preset=today&compare=previous_period&granularity=hour" className="inline-flex min-h-9 items-center gap-1 rounded-control px-2 text-xs font-semibold text-accent hover:bg-accent-soft">Open analytics<ArrowRight className="h-3.5 w-3.5" /></Link></div>
      </div>
      {comparison.isLoading ? <div aria-label="Loading today KPI changes" className="grid gap-2 p-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} className="h-24 w-full" />)}</div> : comparison.isError ? <div className="p-5"><ErrorState message={apiErrorMessage(comparison.error)} onRetry={() => void comparison.refetch()} /></div> : <div className="grid sm:grid-cols-2 xl:grid-cols-3">{rows.map((row) => { const tone = row.sentiment === "positive" ? "text-success" : row.sentiment === "negative" ? "text-danger" : "text-text-secondary"; return <div key={row.key} className="border-b border-border p-4 sm:border-r"><div className="flex items-start justify-between gap-2"><div><p className="text-xs font-semibold text-text-secondary">{row.label}</p><p className="mt-1 text-xl font-bold tabular-nums text-text-primary">{row.current}</p></div><Badge tone={row.sentiment === "positive" ? "success" : row.sentiment === "negative" ? "danger" : "neutral"}>{row.changed ? "Changed" : "Stable"}</Badge></div><div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-2 text-xs"><span className="text-text-disabled">Previous {row.previous}</span><span className={`font-semibold tabular-nums ${tone}`}>{row.change}</span></div></div>; })}</div>}
    </Card>
  );
}

export function OperationalDashboard(): JSX.Element {
  const { user } = useAuth();
  const canReactivation = useHasPermission("reactivation:read");
  const canKyc = useHasPermission("kyc:read");
  const canCampaigns = useHasPermission("campaigns:read");
  const canInbox = useHasPermission("inbox:read");
  const canTemplates = useHasPermission("templates:read");
  const canTasks = useHasPermission("tasks:read");
  const canAnalytics = useHasPermission("analytics:read");

  const pipeline = useReactivationPipeline({ limit: 200 }, canReactivation);
  const kyc = useKycOperations({ limit: 200 }, canKyc);
  const campaigns = useCampaigns(canCampaigns);
  const conversations = useConversations({}, null, 50, canInbox);
  const templates = useTemplates(canTemplates);
  const comparison = useAnalyticsComparison(TODAY_FILTERS, canAnalytics);

  const cards = useMemo(() => pipeline.data?.data ?? [], [pipeline.data?.data]);
  const kycRows = useMemo(() => kyc.data?.data ?? [], [kyc.data?.data]);
  const campaignRows = useMemo(() => campaigns.data ?? [], [campaigns.data]);
  const conversationRows = useMemo(() => conversations.data?.data ?? [], [conversations.data?.data]);
  const templateRows = useMemo(() => templates.data ?? [], [templates.data]);

  const blocked = useMemo(() => blockedReactivationCards(cards), [cards]);
  const reviews = useMemo(() => pendingKycReviews(kycRows), [kycRows]);
  const sim = useMemo(() => delayedSimCards(cards), [cards]);
  const activations = useMemo(() => overdueActivationCards(cards), [cards]);
  const campaignActionRows = useMemo(() => campaignsNeedingAction(campaignRows), [campaignRows]);
  const replyRows = useMemo(() => conversationsNeedingReply(conversationRows), [conversationRows]);
  const templateActionRows = useMemo(() => templatesNeedingAction(templateRows), [templateRows]);
  const agentRows = useMemo(() => agentAttention(cards, kycRows), [cards, kycRows]);
  const attentionItems = useMemo(() => buildAttentionQueue({ reactivation: cards, kyc: kycRows, campaigns: campaignRows, conversations: conversationRows, templates: templateRows }), [cards, kycRows, campaignRows, conversationRows, templateRows]);

  const unavailable = [
    canReactivation && pipeline.isError ? "Reactivation" : null,
    canKyc && kyc.isError ? "KYC" : null,
    canCampaigns && campaigns.isError ? "Campaigns" : null,
    canInbox && conversations.isError ? "Inbox" : null,
    canTemplates && templates.isError ? "Templates" : null,
  ].filter((item): item is string => Boolean(item));
  const loading = pipeline.isLoading || kyc.isLoading || campaigns.isLoading || conversations.isLoading || templates.isLoading;

  function refreshAll(): void {
    if (canReactivation) void pipeline.refetch();
    if (canKyc) void kyc.refetch();
    if (canCampaigns) void campaigns.refetch();
    if (canInbox) void conversations.refetch();
    if (canTemplates) void templates.refetch();
    if (canAnalytics) void comparison.refetch();
  }

  const visibleSources = [canReactivation, canKyc, canCampaigns, canInbox, canTemplates, canTasks, canAnalytics].filter(Boolean).length;
  if (visibleSources === 0) {
    return <EmptyState icon={<Activity className="h-7 w-7" />} title="No operational dashboard sources are available" description="Your current role has no read permission for the Dashboard’s operational queues." />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-border bg-surface-2 px-3 py-2.5">
        <p className="text-xs leading-5 text-text-secondary"><strong className="text-text-primary">Decision scope:</strong> real authorized records from the current tenant. Conversation waiting time is derived from unread age and is not presented as a configured SLA.</p>
        <Button variant="secondary" size="sm" leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />} onClick={refreshAll}>Refresh dashboard</Button>
      </div>

      <AttentionSummary blocked={blocked.length} pendingKyc={reviews.length} delayedSim={sim.length} overdueActivations={activations.length} campaignActions={campaignActionRows.length} replies={replyRows.length} templateActions={templateActionRows.length} agents={agentRows.length} queryState={{ reactivation: { loading: pipeline.isLoading, error: pipeline.isError }, kyc: { loading: kyc.isLoading, error: kyc.isError }, campaigns: { loading: campaigns.isLoading, error: campaigns.isError }, inbox: { loading: conversations.isLoading, error: conversations.isError }, templates: { loading: templates.isLoading, error: templates.isError } }} permissions={{ reactivation: canReactivation, kyc: canKyc, campaigns: canCampaigns, inbox: canInbox, templates: canTemplates, tasks: canTasks }} />

      <div className={`grid gap-5 ${canTasks ? "xl:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.7fr)]" : ""}`}>
        <AttentionQueue items={attentionItems} loading={loading} unavailable={unavailable} />
        {canTasks ? <MyWorkSnapshot userId={user?.id} /> : null}
      </div>

      {(canReactivation || canKyc) ? <div className="grid gap-5 xl:grid-cols-2">{canReactivation ? <BlockedCustomers cards={blocked} loading={pipeline.isLoading} error={pipeline.isError ? pipeline.error : null} onRetry={() => void pipeline.refetch()} /> : null}<AgentAttention rows={agentRows} loading={(canReactivation && pipeline.isLoading) || (canKyc && kyc.isLoading)} errors={(canReactivation && pipeline.isError) || (canKyc && kyc.isError)} /></div> : null}

      {canKyc && reviews.length > 0 ? <Card padding={false} className="overflow-hidden"><CardHeader className="border-b border-border px-4 py-4 sm:px-5" title="KYC reviews pending" description="Reviewer action, evidence completeness and SLA remain visible before opening the case" icon={<FileWarning aria-hidden className="h-4 w-4" />} action={<Link to="/reactivation/kyc" className="inline-flex min-h-9 items-center gap-1 rounded-control px-2 text-xs font-semibold text-accent hover:bg-accent-soft">Open KYC queue<ArrowRight className="h-3.5 w-3.5" /></Link>} /><ul className="grid divide-y divide-border md:grid-cols-2 md:divide-x md:divide-y-0">{reviews.slice(0, 4).map((row) => <li key={row.id} className="p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-text-primary">{row.contact_name}</p><p className="mt-0.5 text-xs text-text-secondary">{row.owner_name ?? "Unassigned"} · {row.progress_percent}% complete</p></div><Badge tone={row.sla_status === "breached" ? "danger" : "warning"}>{KYC_STATUS_LABELS[row.status]}</Badge></div><div className="mt-3 flex flex-wrap gap-1"><Badge tone={row.checklist_complete ? "success" : "warning"}>{row.checklist_complete ? "Evidence complete" : `${row.checklist.length}/2 evidence linked`}</Badge>{row.sla_status === "breached" ? <Badge tone="danger">SLA breached</Badge> : null}</div></li>)}</ul></Card> : null}

      <TodayKpis comparison={comparison} canAnalytics={canAnalytics} />
    </div>
  );
}
