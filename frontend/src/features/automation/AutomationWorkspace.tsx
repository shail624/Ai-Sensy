import { Plus, Search, Workflow } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Modal, Skeleton } from "@/components/ui";
import { AutomationBuilder } from "@/features/automation/AutomationBuilder";
import { apiErrorMessage, useAutomation, useAutomations, useCreateAutomation } from "@/features/automation/api";
import type { AutomationStatus } from "@/features/automation/types";
import { useHasPermission } from "@/lib/auth";

const inputClass = "min-h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-focus focus:ring-2 focus:ring-focus/20";

export function AutomationWorkspace(): JSX.Element {
  const canWrite = useHasPermission("automations:write");
  const canPublish = useHasPermission("automations:publish");
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<AutomationStatus | "all">("all");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const list = useAutomations(q, status);
  const selectedId = params.get("flow");
  const detail = useAutomation(selectedId);
  const create = useCreateAutomation();

  useEffect(() => {
    if (!selectedId && list.data?.data[0]) setParams({ flow: list.data.data[0].id }, { replace: true });
  }, [list.data, selectedId, setParams]);

  async function createFlow(): Promise<void> {
    const flow = await create.mutateAsync({ name, description: description || null, graph: { nodes: [], edges: [] } });
    setCreating(false); setName(""); setDescription(""); setParams({ flow: flow.id });
  }

  return <>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-3 shadow-sm">
      <div className="flex min-w-0 flex-1 flex-wrap gap-2">
        <label className="relative min-w-52 flex-1"><Search aria-hidden className="absolute left-3 top-3 h-4 w-4 text-text-disabled" /><span className="sr-only">Search automations</span><input className={`${inputClass} pl-9`} value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search automations" /></label>
        <label><span className="sr-only">Filter status</span><select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value as AutomationStatus | "all")}><option value="all">All statuses</option><option value="draft">Draft</option><option value="published">Published</option><option value="disabled">Disabled</option></select></label>
      </div>
      {canWrite ? <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>New automation</Button> : null}
    </div>

    <div className="grid gap-4 2xl:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="h-fit rounded-2xl border border-border bg-surface p-3 shadow-sm"><div className="flex items-center justify-between px-2 py-1"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Your automations</h2><Badge tone="neutral">{list.data?.total ?? 0}</Badge></div>
        {list.isLoading ? <div className="mt-3 space-y-2"><Skeleton className="h-16" /><Skeleton className="h-16" /><Skeleton className="h-16" /></div> : null}
        {list.error ? <div className="mt-3"><ErrorState message={apiErrorMessage(list.error)} onRetry={() => void list.refetch()} /></div> : null}
        <div className="mt-3 space-y-2">{list.data?.data.map((flow) => <button key={flow.id} type="button" onClick={() => setParams({ flow: flow.id })} aria-pressed={selectedId === flow.id} className={`w-full rounded-xl border p-3 text-left transition ${selectedId === flow.id ? "border-accent bg-accent-soft" : "border-border bg-surface-2 hover:border-accent"}`}><div className="flex items-start justify-between gap-2"><span className="truncate text-sm font-semibold text-text-primary">{flow.name}</span><Badge tone={flow.status === "published" ? "success" : flow.status === "disabled" ? "warning" : "neutral"}>{flow.status}</Badge></div><p className="mt-1 text-[11px] text-text-disabled">{flow.active_version_no ? `Version ${flow.active_version_no}` : "Not published"}{flow.has_unpublished_changes ? " · draft changes" : ""}</p></button>)}</div>
        {list.data?.total === 0 ? <div className="py-8"><EmptyState title={q || status !== "all" ? "No matches" : "No automations yet"} description={q || status !== "all" ? "Try another search or status." : "Create a workflow draft and publish it when its checks pass."} /></div> : null}
      </aside>

      <main className="min-w-0">{detail.isLoading && selectedId ? <div className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-[36rem]" /></div> : null}{detail.error ? <ErrorState message={apiErrorMessage(detail.error)} onRetry={() => void detail.refetch()} /> : null}{detail.data ? <AutomationBuilder key={detail.data.id} flow={detail.data} canWrite={canWrite} canPublish={canPublish} /> : null}{!selectedId && !list.isLoading ? <div className="flex min-h-96 items-center justify-center rounded-2xl border border-dashed border-border bg-surface"><EmptyState icon={<Workflow className="h-7 w-7" />} title="Choose an automation" description="Select a workflow to review its draft and publication history." /></div> : null}</main>
    </div>

    {creating ? <Modal title="New automation" onClose={() => setCreating(false)}><form onSubmit={(event) => { event.preventDefault(); void createFlow(); }} className="space-y-4"><label className="block text-sm font-medium text-text-secondary">Name<input autoFocus className={`${inputClass} mt-1`} required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} placeholder="Lead welcome workflow" /></label><label className="block text-sm font-medium text-text-secondary">Description<textarea className={`${inputClass} mt-1 min-h-24 py-2`} maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the business outcome" /></label>{create.error ? <ErrorState message={apiErrorMessage(create.error)} /> : null}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setCreating(false)}>Cancel</Button><Button type="submit" loading={create.isPending} disabled={!name.trim()}>Create draft</Button></div></form></Modal> : null}
  </>;
}
