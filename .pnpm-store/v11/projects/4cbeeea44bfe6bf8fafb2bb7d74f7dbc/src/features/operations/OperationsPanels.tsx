import { useQuery } from "@tanstack/react-query";
import { Activity, Braces, FileClock, RadioTower, ServerCog, Webhook } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Card, CardHeader, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useNumbers, useWabas } from "@/features/channels/api";
import { api } from "@/lib/api/client";
import { apiErrorMessage, unwrap } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

type Health = components["schemas"]["HealthResponse"];
type Ready = components["schemas"]["ReadyResponse"];

const PANELS = [
  { title: "Jobs", description: "Inspect requested background work and outcomes.", path: "/operations/jobs", icon: FileClock },
  { title: "Queues & workers", description: "Watch backlog, coverage, retries, and dead-letter attention.", path: "/operations/queues", icon: ServerCog },
  { title: "System health", description: "Verify application liveness and dependency readiness.", path: "/operations/health", icon: Activity },
  { title: "API access", description: "Manage credentials through the existing audited key controls.", path: "/operations/api", icon: Braces },
  { title: "Webhooks", description: "Review channel connectivity and webhook operating boundaries.", path: "/operations/webhooks", icon: Webhook },
  { title: "Logs", description: "Understand structured logging and production query boundaries.", path: "/operations/logs", icon: RadioTower },
] as const;

export function OperationsOverview(): JSX.Element {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {PANELS.map((panel) => {
        const Icon = panel.icon;
        return (
          <Link key={panel.path} to={panel.path} className="group">
            <Card interactive className="h-full">
              <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-5 w-5" /></span>
              <h2 className="font-bold text-text-primary">{panel.title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-text-secondary">{panel.description}</p>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}

export function SystemHealthPanel(): JSX.Element {
  const health = useQuery({ queryKey: ["system", "health"], queryFn: async (): Promise<Health> => unwrap(await api.GET("/health")), refetchInterval: 30_000 });
  const ready = useQuery({ queryKey: ["system", "ready"], queryFn: async (): Promise<Ready> => unwrap(await api.GET("/ready")), refetchInterval: 30_000, retry: false });

  if (health.isLoading || ready.isLoading) return <div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-44 rounded-2xl" /><Skeleton className="h-44 rounded-2xl" /></div>;
  if (health.isError || ready.isError) return <ErrorState message={apiErrorMessage(health.error ?? ready.error)} onRetry={() => { void health.refetch(); void ready.refetch(); }} />;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader title="Application process" description={`${health.data?.service ?? "Service"} · ${health.data?.version ?? "Unknown version"}`} icon={<Activity className="h-5 w-5" />} action={<Badge tone="success" dot>Live</Badge>} />
        <p className="mt-4 text-sm text-text-secondary">Environment: <span className="font-semibold text-text-primary">{health.data?.environment}</span></p>
      </Card>
      <Card>
        <CardHeader title="Dependency readiness" description="Database, broker, and required runtime services" icon={<ServerCog className="h-5 w-5" />} action={<Badge tone={ready.data?.status === "ready" ? "success" : "danger"} dot>{ready.data?.status ?? "Unknown"}</Badge>} />
        <div className="mt-4 space-y-2">
          {(ready.data?.dependencies ?? []).map((dependency) => (
            <div key={dependency.name} className="flex items-center justify-between rounded-lg bg-surface-subtle px-3 py-2 text-sm"><span className="font-medium text-text-primary">{dependency.name}</span><Badge tone={dependency.status === "up" ? "success" : "danger"}>{dependency.status}</Badge></div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export function WebhooksPanel(): JSX.Element {
  const wabas = useWabas();
  const numbers = useNumbers();
  if (wabas.isLoading || numbers.isLoading) return <Skeleton className="h-52 rounded-2xl" />;
  if (wabas.isError || numbers.isError) return <ErrorState message={apiErrorMessage(wabas.error ?? numbers.error)} />;
  return (
    <Card>
      <CardHeader title="WhatsApp webhook surface" description="Connectivity is derived from configured accounts and numbers; the repository has no webhook-event query endpoint." icon={<Webhook className="h-5 w-5" />} action={<Link to="/channels/accounts" className="text-sm font-semibold text-accent hover:underline">Manage channels</Link>} />
      <div className="mt-4 grid grid-cols-2 gap-3"><div className="rounded-xl bg-surface-subtle p-4"><p className="text-2xl font-bold text-text-primary">{wabas.data?.length ?? 0}</p><p className="text-xs text-text-secondary">Business accounts</p></div><div className="rounded-xl bg-surface-subtle p-4"><p className="text-2xl font-bold text-text-primary">{numbers.data?.length ?? 0}</p><p className="text-xs text-text-secondary">Connected numbers</p></div></div>
      <p className="mt-4 rounded-xl border border-border bg-surface-subtle p-3 text-sm leading-relaxed text-text-secondary">Event payloads stay in structured application logs and audited domain state. A searchable delivery log requires production log infrastructure; this screen does not fabricate an event history.</p>
    </Card>
  );
}

export function LogsPanel(): JSX.Element {
  return <Card><EmptyState title="Logs are queried in production observability" description="The application emits structured, redacted logs, but the repository intentionally exposes no log-search API. Connect the production log sink to provide retention, access controls, and queries without weakening tenant or secret boundaries." /></Card>;
}
