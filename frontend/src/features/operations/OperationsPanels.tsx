import { useQuery } from "@tanstack/react-query";
import { Activity, Braces, FileClock, RadioTower, ServerCog, Webhook } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, type BadgeTone, Button, Card, CardHeader, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useNumbers, useWabas } from "@/features/channels/api";
import {
  useDiscardDeadLetter,
  useHasPermission,
  useReplayDeadLetter,
  useWebhookDeadLetters,
  useWebhookEvents,
} from "@/features/operations/api";
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

const EVENT_TONES: Record<string, BadgeTone> = {
  processed: "success",
  received: "info",
  duplicate: "neutral",
  failed: "danger",
};

function shortTime(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

/**
 * The webhook surface: connectivity, then the deliveries themselves.
 *
 * The delivery log and the dead-letter queue need `webhooks:manage`, which is a narrower audience
 * than this page's `waba:read`. Rather than hide the whole panel from someone who may legitimately
 * read channel connectivity, the tables are the part that is gated.
 */
export function WebhooksPanel(): JSX.Element {
  const wabas = useWabas();
  const numbers = useNumbers();
  const canOperate = useHasPermission("webhooks:manage");
  const events = useWebhookEvents("", canOperate);
  const deadLetters = useWebhookDeadLetters("pending", canOperate);
  const replay = useReplayDeadLetter();
  const discard = useDiscardDeadLetter();

  if (wabas.isLoading || numbers.isLoading) return <Skeleton className="h-52 rounded-2xl" />;
  if (wabas.isError || numbers.isError) return <ErrorState message={apiErrorMessage(wabas.error ?? numbers.error)} />;

  const parked = deadLetters.data?.page.total ?? 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="WhatsApp webhook surface" description="Connectivity is derived from configured accounts and numbers." icon={<Webhook className="h-5 w-5" />} action={<Link to="/channels/accounts" className="text-sm font-semibold text-accent hover:underline">Manage channels</Link>} />
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-surface-subtle p-4"><p className="text-2xl font-bold text-text-primary">{wabas.data?.length ?? 0}</p><p className="text-xs text-text-secondary">Business accounts</p></div>
          <div className="rounded-xl bg-surface-subtle p-4"><p className="text-2xl font-bold text-text-primary">{numbers.data?.length ?? 0}</p><p className="text-xs text-text-secondary">Connected numbers</p></div>
          {canOperate ? (
            <div className="rounded-xl bg-surface-subtle p-4">
              <p className={`text-2xl font-bold ${parked > 0 ? "text-danger" : "text-text-primary"}`}>{parked}</p>
              <p className="text-xs text-text-secondary">Parked for a human</p>
            </div>
          ) : null}
        </div>
      </Card>

      {!canOperate ? (
        <Card>
          <EmptyState title="Delivery log requires webhook permissions" description="Viewing inbound deliveries and the dead-letter queue needs `webhooks:manage`, the same permission as replaying an event." />
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader title="Recent deliveries" description="Newest first. Message content is not shown here — it belongs to the Inbox, behind its own permission." icon={<Webhook className="h-5 w-5" />} />
            {events.isPending ? (
              <Skeleton className="mt-4 h-40 rounded-xl" />
            ) : events.isError ? (
              <div className="mt-4"><ErrorState message={apiErrorMessage(events.error)} onRetry={() => void events.refetch()} /></div>
            ) : events.data && events.data.data.length > 0 ? (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-secondary">
                    <th scope="col" className="pb-2 pr-3 font-medium">Received</th>
                    <th scope="col" className="pb-2 pr-3 font-medium">Type</th>
                    <th scope="col" className="pb-2 pr-3 font-medium">Status</th>
                    <th scope="col" className="pb-2 pr-3 font-medium">Attempts</th>
                    <th scope="col" className="pb-2 font-medium">Signature</th>
                  </tr></thead>
                  <tbody>
                    {events.data.data.map((event) => (
                      <tr key={`${event.event_id ?? "anon"}-${event.created_at}`} className="border-b border-border/60 last:border-0">
                        <td className="py-2 pr-3 text-text-secondary">{shortTime(event.created_at)}</td>
                        <td className="py-2 pr-3 text-text-primary">{event.object_type ?? "—"}</td>
                        <td className="py-2 pr-3"><Badge tone={EVENT_TONES[event.status] ?? "neutral"}>{event.status}</Badge></td>
                        <td className="py-2 pr-3 text-text-secondary">{event.attempts}</td>
                        <td className="py-2">{event.signature_ok ? <Badge tone="success">verified</Badge> : <Badge tone="danger">unverified</Badge>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-3 text-xs text-text-secondary">Showing {events.data.data.length} of {events.data.page.total ?? events.data.data.length} recorded deliveries.</p>
              </div>
            ) : (
              <div className="mt-4"><EmptyState title="No deliveries recorded" description="Nothing has arrived on this organization's webhook routes yet. If you expected traffic, check the channel connection first." /></div>
            )}
          </Card>

          <Card>
            <CardHeader title="Parked events" description="Retries exhausted and waiting for a human. The error is what says which." icon={<Webhook className="h-5 w-5" />} />
            {deadLetters.isPending ? (
              <Skeleton className="mt-4 h-24 rounded-xl" />
            ) : deadLetters.isError ? (
              <div className="mt-4"><ErrorState message={apiErrorMessage(deadLetters.error)} onRetry={() => void deadLetters.refetch()} /></div>
            ) : deadLetters.data && deadLetters.data.data.length > 0 ? (
              <>
              <ul className="mt-4 space-y-2">
                {deadLetters.data.data.map((entry) => (
                  <li key={entry.id} className="rounded-xl border border-border bg-surface-subtle p-3">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                      <span>{shortTime(entry.created_at)}</span>
                      <Badge tone="neutral">{entry.attempts} attempts</Badge>
                    </div>
                    <p className="mt-1 text-sm text-text-primary">{entry.error_detail ?? "No error was recorded."}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={replay.isPending || discard.isPending}
                        onClick={() => replay.mutate(entry.id)}
                      >
                        Try again
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        disabled={replay.isPending || discard.isPending}
                        onClick={() => discard.mutate(entry.id)}
                      >
                        Discard
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
              {replay.isError || discard.isError ? (
                <p role="alert" className="mt-3 text-xs text-danger">
                  {apiErrorMessage(replay.error ?? discard.error)}
                </p>
              ) : null}
              </>
            ) : (
              <div className="mt-4"><EmptyState title="Nothing is parked" description="Every event that arrived was processed or recognised as a duplicate." /></div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

export function LogsPanel(): JSX.Element {
  return <Card><EmptyState title="Logs are not shown here" description="The app writes its logs to the server's logging system. Ask your technical team to search them there — this keeps private data out of the app." /></Card>;
}
