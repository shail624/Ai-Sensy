import {
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Eye,
  Megaphone,
  MessageSquareText,
  Send,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";

import { PageContainer, PageHeader } from "@/components/layout";
import { Button, Card, CardHeader, SkeletonStat, StatCard } from "@/components/ui";
import { useAnalyticsSummary } from "@/features/analytics/api";
import { formatKpi } from "@/features/analytics/format";
import type { AnalyticsFilterState } from "@/features/analytics/types";
import { MyWorkQueue } from "@/features/tasks";
import { useAuth, useHasPermission } from "@/lib/auth";

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

const HEADLINE = [
  { key: "delivery_rate", label: "Delivery rate", kind: "rate", icon: Send },
  { key: "read_rate", label: "Read rate", kind: "rate", icon: Eye },
  { key: "failure_rate", label: "Failure rate", kind: "rate", icon: TriangleAlert },
  { key: "avg_first_response_seconds", label: "First response", kind: "duration", icon: Clock3 },
] as const;

function KpiRow(): JSX.Element {
  const summary = useAnalyticsSummary(DASH_FILTERS);
  const kpis = summary.data?.kpis;

  if (summary.isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {HEADLINE.map((headline) => <SkeletonStat key={headline.key} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {HEADLINE.map((headline) => {
        const Icon = headline.icon;
        return (
          <StatCard
            key={headline.key}
            label={headline.label}
            value={formatKpi(kpis?.[headline.key] ?? null, headline.kind)}
            icon={<Icon aria-hidden className="h-4 w-4" />}
            hint="7 days"
          />
        );
      })}
    </div>
  );
}

export function DashboardPage(): JSX.Element {
  const { user, hasPermission } = useAuth();
  const canAnalytics = useHasPermission("analytics:read");
  const canCampaigns = useHasPermission("campaigns:read");
  const canInbox = useHasPermission("inbox:read");
  const canTasks = useHasPermission("tasks:read");
  const firstName = user?.full_name.trim().split(/\s+/)[0] ?? "there";
  const setupActions = [
    hasPermission("waba:read") ? { label: "Connect your WhatsApp number", path: "/settings/whatsapp" } : null,
    hasPermission("contacts:import") ? { label: "Import your contacts", path: "/contacts?import=1" } : null,
    hasPermission("templates:write") ? { label: "Create a message template", path: "/templates/new" } : null,
  ].filter((item): item is { label: string; path: string } => item !== null);

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description={`${greeting()}, ${firstName}. Here’s what needs your attention today.`}
        actions={
          <>
            {canInbox ? (
              <Link to="/inbox">
                <Button variant="secondary" leftIcon={<MessageSquareText className="h-4 w-4" />}>
                  Live chat
                </Button>
              </Link>
            ) : null}
            {canCampaigns ? (
              <Link to="/campaigns/new">
                <Button leftIcon={<Megaphone className="h-4 w-4" />}>New campaign</Button>
              </Link>
            ) : null}
          </>
        }
      />

      {canAnalytics ? (
        <section aria-label="Key indicators" className="mb-5">
          <KpiRow />
        </section>
      ) : null}

      <div className={`grid grid-cols-1 gap-5 ${canTasks && setupActions.length > 0 ? "lg:grid-cols-[minmax(0,1fr)_20rem]" : ""}`}>
        {canTasks ? (
          <Card padding={false} className="p-4 sm:p-5">
            <CardHeader
              title="My work"
              description="Follow-ups assigned to you"
              icon={<CheckCircle2 aria-hidden className="h-[18px] w-[18px]" />}
              action={
                <Link to="/tasks">
                  <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
                    View all
                  </Button>
                </Link>
              }
            />
            <div className="mt-3"><MyWorkQueue /></div>
          </Card>
        ) : null}

        <aside className="space-y-4">
          {setupActions.length > 0 ? (
            <Card>
              <CardHeader title="Get started" description="Complete the basics" />
              <div className="mt-2 space-y-1">
                {setupActions.map((item, index) => (
                  <Link key={item.path} to={item.path} className="flex items-center gap-2.5 rounded-lg px-2 py-2 hover:bg-hover">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft text-[10px] font-bold text-accent">{index + 1}</span>
                    <span className="text-sm font-medium text-text-primary">{item.label}</span>
                  </Link>
                ))}
              </div>
            </Card>
          ) : null}
        </aside>
      </div>
    </PageContainer>
  );
}
