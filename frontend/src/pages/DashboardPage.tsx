import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Eye,
  Megaphone,
  MessageSquareText,
  Send,
  ServerCog,
  TriangleAlert,
  UserPlus,
} from "lucide-react";
import { lazy, Suspense, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { PageContainer, visibleNavItems } from "@/components/layout";
import { Badge, Button, Card, CardHeader, EmptyState, Skeleton, SkeletonStat, StatCard } from "@/components/ui";
import {
  useAnalyticsFreshness,
  useAnalyticsSeries,
  useAnalyticsSummary,
} from "@/features/analytics/api";
import { formatKpi, formatLag } from "@/features/analytics/format";
// Lazy so recharts (~400 kB) stays in the on-demand analytics chunk rather than the eager bundle
// the whole app loads — the Design Book's "lazy-load analytics chunk" performance rule.
const SeriesChart = lazy(() =>
  import("@/features/analytics/SeriesChart").then((m) => ({ default: m.SeriesChart })),
);
import { DEFAULT_SERIES_METRICS } from "@/features/analytics/types";
import type { AnalyticsFilterState } from "@/features/analytics/types";
import { useQueues } from "@/features/operations/api";
import { MyWorkQueue } from "@/features/tasks";
import { useAuth, useHasPermission } from "@/lib/auth";

// A fixed 7-day daily window is the right default for an at-a-glance health read; the full
// Analytics screen owns the range picker.
const DASH_FILTERS: AnalyticsFilterState = {
  preset: "last_7d",
  from: "",
  to: "",
  granularity: "day",
  compare: "",
};

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

// --- Headline KPIs -------------------------------------------------------------------------------
const HEADLINE = [
  { key: "delivery_rate", label: "Delivery rate", kind: "rate", icon: Send, invert: false },
  { key: "read_rate", label: "Read rate", kind: "rate", icon: Eye, invert: false },
  { key: "failure_rate", label: "Failure rate", kind: "rate", icon: TriangleAlert, invert: true },
  { key: "avg_first_response_seconds", label: "Avg first response", kind: "duration", icon: Clock3, invert: true },
] as const;

function KpiRow(): JSX.Element {
  const summary = useAnalyticsSummary(DASH_FILTERS);
  const kpis = summary.data?.kpis;

  if (summary.isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {HEADLINE.map((h) => (
          <SkeletonStat key={h.key} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {HEADLINE.map((h) => {
        const Icon = h.icon;
        return (
          <StatCard
            key={h.key}
            label={h.label}
            value={formatKpi(kpis?.[h.key] ?? null, h.kind)}
            icon={<Icon aria-hidden className="h-4 w-4" />}
            hint="last 7 days"
          />
        );
      })}
    </div>
  );
}

function FreshnessBadge(): JSX.Element | null {
  const freshness = useAnalyticsFreshness();
  const rows = freshness.data?.data ?? [];
  if (rows.length === 0) return null;
  const lag = Math.min(...rows.map((r) => r.lag_seconds ?? Number.MAX_SAFE_INTEGER));
  const stale = lag > 30 * 60;
  return (
    <Badge tone={stale ? "warning" : "success"} dot>
      Data {formatLag(lag)}
    </Badge>
  );
}

function DeliveryTrendCard(): JSX.Element {
  const series = useAnalyticsSeries(DASH_FILTERS, DEFAULT_SERIES_METRICS);
  return (
    <Card>
      <CardHeader
        title="Delivery over time"
        description="Sent, delivered, read and failed — last 7 days"
        icon={<Activity aria-hidden className="h-[18px] w-[18px]" />}
        action={
          <Link to="/analytics">
            <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
              Analytics
            </Button>
          </Link>
        }
      />
      <div className="mt-4">
        <Suspense fallback={<Skeleton className="h-[260px] w-full rounded-lg" />}>
          <SeriesChart series={series.data?.series ?? []} kind="area" height={260} />
        </Suspense>
      </div>
    </Card>
  );
}

function healthRow(
  label: string,
  value: ReactNode,
  tone: "success" | "warning" | "danger" | "neutral" | "info",
): JSX.Element {
  return (
    <div className="flex items-center justify-between border-t border-border py-2.5 first:border-t-0">
      <span className="text-sm text-text-secondary">{label}</span>
      <Badge tone={tone} dot>
        {value}
      </Badge>
    </div>
  );
}

function SystemHealthCard(): JSX.Element {
  const queues = useQueues();
  const snapshot = queues.data;
  const depth = (snapshot?.queues ?? []).reduce((sum, q) => sum + q.depth, 0);
  const workers = snapshot?.workers ?? [];
  const running = workers.reduce((sum, w) => sum + w.active_tasks, 0);
  const parked = snapshot?.dead_letter_parked ?? 0;

  return (
    <Card>
      <CardHeader
        title="System health"
        description="Queues, workers and background jobs"
        icon={<ServerCog aria-hidden className="h-[18px] w-[18px]" />}
        action={
          <Link to="/operations">
            <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
              Operations
            </Button>
          </Link>
        }
      />
      <div className="mt-3">
        {healthRow("Workers online", `${workers.length} live`, workers.length > 0 ? "success" : "danger")}
        {healthRow("Tasks running", running, running > 0 ? "info" : "neutral")}
        {healthRow("Queue backlog", depth, depth > 100 ? "warning" : depth > 0 ? "info" : "success")}
        {healthRow(
          "Dead-letter",
          parked === 0 ? "none" : `${parked} parked`,
          parked > 0 ? "danger" : "success",
        )}
      </div>
    </Card>
  );
}

export function DashboardPage(): JSX.Element {
  const { user, hasPermission } = useAuth();
  const canAnalytics = useHasPermission("analytics:read");
  const canSystem = useHasPermission("system:read");
  const canCampaigns = useHasPermission("campaigns:read");
  const canContacts = useHasPermission("contacts:read");
  const firstName = user?.full_name.trim().split(/\s+/)[0] ?? "there";

  const exploreCards = visibleNavItems(hasPermission).filter(
    (item) => item.path !== "/" && item.path !== "/settings",
  );

  return (
    <PageContainer>
      {/* Hero */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <p className="text-2xl font-bold tracking-tight text-text-primary">
              {greeting()}, {firstName}
            </p>
            {canAnalytics ? <FreshnessBadge /> : null}
          </div>
          <p className="mt-1 text-sm text-text-secondary">
            {"Here's how your WhatsApp messaging is performing today."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canContacts ? (
            <Link to="/contacts">
              <Button variant="secondary" leftIcon={<UserPlus className="h-4 w-4" />}>
                Add contact
              </Button>
            </Link>
          ) : null}
          {canCampaigns ? (
            <Link to="/campaigns">
              <Button leftIcon={<Megaphone className="h-4 w-4" />}>New campaign</Button>
            </Link>
          ) : null}
        </div>
      </div>

      {canAnalytics ? (
        <section aria-label="Key indicators" className="mb-6">
          <KpiRow />
        </section>
      ) : null}

      {/* Main grid: trend + work queue on the left, health + shortcuts on the right */}
      <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          {canAnalytics ? <DeliveryTrendCard /> : null}
          <Card padding={false} className="p-5">
            <CardHeader
              title="My work queue"
              description="Follow-ups assigned to you"
              icon={<CheckCircle2 aria-hidden className="h-[18px] w-[18px]" />}
              action={
                <Link to="/tasks">
                  <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
                    All tasks
                  </Button>
                </Link>
              }
            />
            <div className="mt-4">
              <MyWorkQueue />
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          {canSystem ? <SystemHealthCard /> : null}
          <Card>
            <CardHeader
              title="Jump back in"
              description="Your most-used areas"
              icon={<MessageSquareText aria-hidden className="h-[18px] w-[18px]" />}
            />
            <div className="mt-3 grid grid-cols-1 gap-1">
              {exploreCards.slice(0, 6).map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className="group flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                      <Icon aria-hidden className="h-4 w-4" />
                    </span>
                    <span className="flex-1 text-sm font-medium text-text-primary">{item.label}</span>
                    <ArrowUpRight
                      aria-hidden
                      className="h-4 w-4 text-text-disabled opacity-0 transition-opacity group-hover:opacity-100"
                    />
                  </Link>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* Explore — everything the user can reach, never an empty page */}
      <section aria-label="Modules">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">Explore</h2>
        {exploreCards.length === 0 ? (
          <Card>
            <EmptyState
              title="Nothing to show yet"
              description="Your account doesn't have access to any modules. Ask an administrator to grant a role."
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {exploreCards.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.path} to={item.path} aria-label={item.label} className="group">
                  <Card interactive className="flex h-full items-start gap-4">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent transition-colors group-hover:bg-accent group-hover:text-accent-fg">
                      <Icon aria-hidden className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5">
                        <span className="font-semibold text-text-primary">{item.label}</span>
                        <ArrowUpRight
                          aria-hidden
                          className="h-4 w-4 text-text-disabled opacity-0 transition-opacity group-hover:opacity-100"
                        />
                      </span>
                      <span className="mt-1 block text-sm leading-relaxed text-text-secondary">
                        {item.description}
                      </span>
                    </span>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </PageContainer>
  );
}
