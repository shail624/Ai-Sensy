import {
  Bell, CheckCircle2, ChevronDown, ChevronUp, Clock3, GitBranch, GripVertical,
  Megaphone, Play, RotateCcw, Save, Send, Tags, Trash2, UserRound, Webhook, Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge, Button, EmptyState, ErrorState, Modal, Spinner } from "@/components/ui";
import {
  apiErrorMessage, useAutomationRun, useAutomationRuns, useAutomationVersions,
  useCreateAutomationTestRun, useDisableAutomation, useEnableAutomation, usePublishAutomation,
  useRestoreAutomation, useUpdateAutomation, useValidateAutomation,
} from "@/features/automation/api";
import type { AutomationEdge, AutomationFlow, AutomationGraph, AutomationNode } from "@/features/automation/types";
import { graphEdges, graphNodes } from "@/features/automation/types";
import { useCampaigns, useTags } from "@/features/campaigns/api";
import { useHasPermission } from "@/lib/auth";
import { createIdempotencyKey } from "@/lib/idempotency";

type NodeKind = AutomationNode["kind"];

const NODE_DEFINITIONS: Record<NodeKind, { label: string; description: string; icon: typeof Zap; customerFacing?: boolean }> = {
  trigger: { label: "Trigger", description: "Start from a verified event or schedule.", icon: Zap },
  condition: { label: "Condition", description: "Continue only when a verified value matches.", icon: GitBranch },
  action: { label: "Create task", description: "Prepare a safe internal follow-up task.", icon: CheckCircle2 },
  delay: { label: "Delay", description: "Pause the future run for a bounded duration.", icon: Clock3 },
  tag: { label: "Apply tag", description: "Reference an existing CRM tag.", icon: Tags },
  assignment: { label: "Assignment", description: "Route work to a user or round-robin queue.", icon: UserRound },
  wait: { label: "Wait for event", description: "Resume after a verified event or timeout.", icon: Clock3 },
  webhook: { label: "Webhook", description: "Reference a future governed outbound integration.", icon: Webhook },
  campaign: { label: "Campaign proposal", description: "Prepare a proposal; never launch directly.", icon: Megaphone, customerFacing: true },
  notification: { label: "Notification", description: "Notify an operator with an internal message.", icon: Bell },
  approval: { label: "Human approval", description: "Mandatory gate before a customer-facing effect.", icon: Send, customerFacing: true },
};

const inputClass = "mt-1 min-h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-focus focus:ring-2 focus:ring-focus/20";
const NIL_UUID = "00000000-0000-0000-0000-000000000000";
let nodeSequence = 0;
const AUTHORABLE_KINDS = (Object.keys(NODE_DEFINITIONS) as NodeKind[]).filter((kind) => kind !== "webhook");

interface EditorConfig {
  event?: string;
  schedule_cron?: string | null;
  field?: string;
  operator?: string;
  value?: unknown;
  title?: string;
  seconds?: number;
  tag_id?: string;
  mode?: string;
  user_id?: string | null;
  timeout_seconds?: number | null;
  webhook_id?: string;
  campaign_id?: string;
  message?: string;
  permission?: string;
}

function createNode(kind: NodeKind): AutomationNode {
  nodeSequence += 1;
  const id = `${kind}-${Date.now()}-${nodeSequence}`;
  const base = { id, kind, label: NODE_DEFINITIONS[kind].label };
  const config: Record<NodeKind, object> = {
    trigger: { event: "contact.created" },
    condition: { field: "opt_in_status", operator: "eq", value: "opted_in" },
    action: { action: "create_task", title: "Follow up with customer" },
    delay: { seconds: 3600 },
    tag: { tag_id: NIL_UUID },
    assignment: { mode: "round_robin", user_id: null },
    wait: { event: "message.received", timeout_seconds: 86400 },
    webhook: { webhook_id: NIL_UUID },
    campaign: { campaign_id: NIL_UUID },
    notification: { message: "A customer needs attention" },
    approval: { permission: "campaigns:send" },
  };
  return { ...base, config: config[kind] } as AutomationNode;
}

function linearGraph(nodes: AutomationNode[]): AutomationGraph {
  return {
    nodes,
    edges: nodes.slice(1).map((node, index) => ({
      id: `edge-${index + 1}-${node.id}`,
      source: nodes[index]!.id,
      target: node.id,
    })),
  };
}

function NodeInspector({ node, onChange, onRemove, tags, campaigns }: { node: AutomationNode; onChange: (node: AutomationNode) => void; onRemove: () => void; tags: { id: string; name: string }[]; campaigns: { id: string; name: string }[] }): JSX.Element {
  const setConfig = (config: object) => onChange({ ...node, config } as AutomationNode);
  const config = node.config as unknown as EditorConfig;
  return <div className="mt-4 space-y-4">
    <label className="block text-xs font-medium text-text-secondary">Step name<input className={inputClass} value={node.label ?? ""} onChange={(event) => onChange({ ...node, label: event.target.value } as AutomationNode)} /></label>
    {node.kind === "trigger" ? <><label className="block text-xs font-medium text-text-secondary">Event<select className={inputClass} value={config.event ?? "contact.created"} onChange={(event) => setConfig({ event: event.target.value, ...(event.target.value === "schedule" ? { schedule_cron: "0 9 * * 1-5" } : {}) })}><option value="contact.created">Contact created</option><option value="message.received">Message received</option><option value="lead.stage_changed">Lead stage changed</option><option value="schedule">Schedule</option></select></label>{config.event === "schedule" ? <label className="block text-xs font-medium text-text-secondary">Cron schedule<input className={inputClass} value={config.schedule_cron ?? ""} onChange={(event) => setConfig({ ...config, schedule_cron: event.target.value })} /></label> : null}</> : null}
    {node.kind === "condition" ? <><label className="block text-xs font-medium text-text-secondary">Field<input className={inputClass} value={config.field ?? ""} onChange={(event) => setConfig({ ...config, field: event.target.value })} /></label><label className="block text-xs font-medium text-text-secondary">Operator<select className={inputClass} value={config.operator ?? "eq"} onChange={(event) => setConfig({ ...config, operator: event.target.value })}>{["eq", "ne", "contains", "exists", "gt", "gte", "lt", "lte"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="block text-xs font-medium text-text-secondary">Value<input className={inputClass} value={typeof config.value === "string" ? config.value : String(config.value ?? "")} onChange={(event) => setConfig({ ...config, value: event.target.value })} /></label></> : null}
    {node.kind === "action" ? <label className="block text-xs font-medium text-text-secondary">Task title<input className={inputClass} value={config.title ?? ""} onChange={(event) => setConfig({ ...config, title: event.target.value })} /></label> : null}
    {node.kind === "delay" ? <label className="block text-xs font-medium text-text-secondary">Delay (seconds)<input className={inputClass} type="number" min={60} max={2592000} value={config.seconds ?? 60} onChange={(event) => setConfig({ seconds: Number(event.target.value) })} /></label> : null}
    {node.kind === "tag" ? <label className="block text-xs font-medium text-text-secondary">Tag<select className={inputClass} value={config.tag_id ?? NIL_UUID} onChange={(event) => setConfig({ tag_id: event.target.value })}><option value={NIL_UUID}>Choose a tag</option>{tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select></label> : null}
    {node.kind === "assignment" ? <label className="block text-xs font-medium text-text-secondary">Routing<select className={inputClass} value={config.mode ?? "round_robin"} onChange={() => setConfig({ mode: "round_robin", user_id: null })}><option value="round_robin">Round robin</option>{config.mode === "user" ? <option value="user">Specific user (existing definition)</option> : null}</select></label> : null}
    {node.kind === "wait" ? <><label className="block text-xs font-medium text-text-secondary">Resume event<select className={inputClass} value={config.event ?? "message.received"} onChange={(event) => setConfig({ ...config, event: event.target.value })}><option value="message.received">Message received</option><option value="lead.stage_changed">Lead stage changed</option><option value="task.completed">Task completed</option></select></label><label className="block text-xs font-medium text-text-secondary">Timeout (seconds)<input className={inputClass} type="number" min={60} max={2592000} value={config.timeout_seconds ?? ""} onChange={(event) => setConfig({ ...config, timeout_seconds: Number(event.target.value) })} /></label></> : null}
    {node.kind === "webhook" ? <label className="block text-xs font-medium text-text-secondary">Governed webhook ID<input className={inputClass} value={config.webhook_id ?? ""} onChange={(event) => setConfig({ webhook_id: event.target.value })} /></label> : null}
    {node.kind === "campaign" ? <label className="block text-xs font-medium text-text-secondary">Campaign<select className={inputClass} value={config.campaign_id ?? NIL_UUID} onChange={(event) => setConfig({ campaign_id: event.target.value })}><option value={NIL_UUID}>Choose a campaign</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></label> : null}
    {node.kind === "notification" ? <label className="block text-xs font-medium text-text-secondary">Internal message<textarea className={`${inputClass} min-h-24 py-2`} value={config.message ?? ""} onChange={(event) => setConfig({ message: event.target.value })} /></label> : null}
    {node.kind === "approval" ? <label className="block text-xs font-medium text-text-secondary">Required permission<select className={inputClass} value={config.permission ?? "campaigns:send"} onChange={(event) => setConfig({ permission: event.target.value })}><option value="campaigns:send">Campaign send</option><option value="messages:send">Message send</option></select></label> : null}
    <Button variant="secondary" block leftIcon={<Trash2 className="h-4 w-4 text-danger" />} onClick={onRemove}>Remove step</Button>
  </div>;
}

export function AutomationBuilder({ flow, canWrite, canPublish }: { flow: AutomationFlow; canWrite: boolean; canPublish: boolean }): JSX.Element {
  const [name, setName] = useState(flow.name);
  const [description, setDescription] = useState(flow.description ?? "");
  const [nodes, setNodes] = useState<AutomationNode[]>(graphNodes(flow.graph));
  const [edges, setEdges] = useState<AutomationEdge[]>(graphEdges(flow.graph));
  const [selected, setSelected] = useState<string | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [testOpen, setTestOpen] = useState(false);
  const [testInput, setTestInput] = useState("{}");
  const [testInputError, setTestInputError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const update = useUpdateAutomation(flow.id);
  const validate = useValidateAutomation(flow.id);
  const resetValidation = validate.reset;
  const publish = usePublishAutomation(flow.id);
  const disable = useDisableAutomation(flow.id);
  const enable = useEnableAutomation(flow.id);
  const restore = useRestoreAutomation(flow.id);
  const versions = useAutomationVersions(flow.id);
  const runs = useAutomationRuns(flow.id);
  const selectedRun = useAutomationRun(selectedRunId);
  const runTest = useCreateAutomationTestRun(flow.id);
  const canReadTags = useHasPermission("contacts:read");
  const canReadCampaigns = useHasPermission("campaigns:read");
  const tags = useTags(canReadTags);
  const campaigns = useCampaigns(canReadCampaigns);

  useEffect(() => {
    setName(flow.name); setDescription(flow.description ?? ""); setNodes(graphNodes(flow.graph)); setEdges(graphEdges(flow.graph));
    setSelected(null); resetValidation();
  }, [flow.id, flow.name, flow.description, flow.graph, resetValidation]);

  useEffect(() => {
    setNotice(null);
  }, [flow.id]);

  useEffect(() => {
    if (!selectedRunId && runs.data?.[0]) setSelectedRunId(runs.data[0].id);
  }, [runs.data, selectedRunId]);

  const graph = useMemo(() => ({ nodes, edges }), [nodes, edges]);
  const dirty = name !== flow.name || description !== (flow.description ?? "") || JSON.stringify(graph) !== JSON.stringify({ nodes: flow.graph.nodes ?? [], edges: flow.graph.edges ?? [] });
  const active = nodes.find((node) => node.id === selected) ?? null;
  const busy = update.isPending || publish.isPending || disable.isPending || enable.isPending || restore.isPending || runTest.isPending;
  const error = update.error ?? validate.error ?? publish.error ?? disable.error ?? enable.error ?? restore.error ?? runTest.error;

  function add(kind: NodeKind): void {
    let node = createNode(kind);
    if (kind === "tag" && tags.data?.[0]) node = { ...node, config: { tag_id: tags.data[0].id } } as AutomationNode;
    if (kind === "campaign" && campaigns.data?.[0]) node = { ...node, config: { campaign_id: campaigns.data[0].id } } as AutomationNode;
    const next = [...nodes, node]; setNodes(next); setEdges(linearGraph(next).edges ?? []); setSelected(node.id); setNotice(null);
  }
  function move(from: number, to: number): void {
    if (from === to) return;
    const next = [...nodes]; const [item] = next.splice(from, 1); if (item) next.splice(to, 0, item); setNodes(next); setEdges(linearGraph(next).edges ?? []);
  }
  async function save(): Promise<AutomationFlow> {
    const saved = await update.mutateAsync({ name, description: description || null, graph, expected_row_version: flow.row_version });
    setNotice("Draft saved safely."); return saved;
  }
  async function publishFlow(): Promise<void> {
    const result = await validate.mutateAsync();
    if (!result.valid) { setNotice("Resolve the validation issues before publishing."); return; }
    await publish.mutateAsync(flow.row_version); setNotice("Immutable version published.");
  }

  async function startTestRun(): Promise<void> {
    let input: unknown;
    try {
      input = JSON.parse(testInput);
    } catch {
      setTestInputError("Enter valid JSON test data.");
      return;
    }
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      setTestInputError("Test data must be one JSON object.");
      return;
    }
    const run = await runTest.mutateAsync({
      input: input as Record<string, unknown>,
      idempotencyKey: createIdempotencyKey(),
    });
    setSelectedRunId(run.id);
    setTestInputError(null);
    setTestOpen(false);
    setNotice("Test run queued safely. Every action will be simulated.");
  }

  return <><div className="space-y-4">
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] lg:items-end">
        <label className="text-xs font-semibold text-text-secondary">Automation name<input className={inputClass} disabled={!canWrite} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="text-xs font-semibold text-text-secondary">Description<input className={inputClass} disabled={!canWrite} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What outcome does this workflow support?" /></label>
        <div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={!canWrite || !dirty || busy} loading={update.isPending} leftIcon={<Save className="h-4 w-4" />} onClick={() => void save()}>Save draft</Button><Button disabled={!canPublish || dirty || busy || !flow.has_unpublished_changes} loading={publish.isPending} leftIcon={<Send className="h-4 w-4" />} onClick={() => void publishFlow()}>Publish</Button></div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-secondary"><Badge tone={flow.status === "published" ? "success" : flow.status === "disabled" ? "warning" : "neutral"}>{flow.status}</Badge>{flow.active_version_no ? <span>Active version {flow.active_version_no}</span> : <span>Not published</span>}{dirty ? <Badge tone="warning">Unsaved changes</Badge> : flow.has_unpublished_changes ? <Badge tone="info">Draft changes ready</Badge> : null}</div>
    </section>

    {error ? <ErrorState message={apiErrorMessage(error)} /> : null}
    {notice ? <div role="status" className="rounded-xl border border-accent/30 bg-accent-soft px-4 py-3 text-sm text-accent">{notice}</div> : null}
    {validate.data && !validate.data.valid ? <div role="alert" className="rounded-xl border border-warning/40 bg-warning-soft p-4"><p className="text-sm font-semibold text-warning">Publication checks need attention</p><ul className="mt-2 space-y-1 text-xs text-text-secondary">{validate.data.issues.map((issue, index) => <li key={`${issue.code}-${issue.node_id ?? index}`}>• {issue.message}</li>)}</ul></div> : null}

    <div className="grid min-h-[36rem] overflow-hidden rounded-2xl border border-border bg-surface shadow-sm xl:grid-cols-[15rem_minmax(0,1fr)_19rem]">
      <aside className="border-b border-border p-3 xl:border-b-0 xl:border-r"><h2 className="px-2 text-xs font-semibold uppercase tracking-wide text-text-disabled">Add a step</h2><div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-1">{AUTHORABLE_KINDS.map((kind) => { const definition = NODE_DEFINITIONS[kind]; const Icon = definition.icon; return <button key={kind} type="button" disabled={!canWrite} onClick={() => add(kind)} className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 text-left text-xs font-semibold text-text-primary hover:border-accent hover:bg-accent-soft disabled:opacity-50"><Icon aria-hidden className="h-4 w-4 text-accent" />{definition.label}</button>; })}</div></aside>

      <section aria-label="Automation flow canvas" className="min-w-0 bg-[radial-gradient(circle_at_top,var(--color-accent-soft),transparent_44%)] p-4 sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-text-primary">Flow</h2><p className="mt-1 text-xs text-text-secondary">Build a clear sequence. Saving and publishing never executes it.</p></div><Badge tone="info">Versioned definition</Badge></div>
        {nodes.length === 0 ? <div className="flex min-h-[26rem] items-center justify-center"><EmptyState title="Start with a trigger" description="Add a trigger, then connect the conditions and actions your team needs." /></div> : <ol className="mx-auto max-w-2xl space-y-3">{nodes.map((node, index) => { const definition = NODE_DEFINITIONS[node.kind]; const Icon = definition.icon; return <li key={node.id} draggable={canWrite} onDragStart={() => setDragging(index)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (dragging !== null) move(dragging, index); setDragging(null); }} className="group flex items-center gap-2"><button type="button" onClick={() => setSelected(node.id)} aria-pressed={selected === node.id} className={`flex min-h-16 min-w-0 flex-1 items-center gap-3 rounded-2xl border bg-surface p-3 text-left shadow-sm transition ${selected === node.id ? "border-accent ring-2 ring-focus/30" : "border-border hover:border-accent"}`}><GripVertical aria-hidden className="h-4 w-4 text-text-disabled" /><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-5 w-5" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-text-primary">{index + 1}. {node.label || definition.label}</span><span className="mt-0.5 block text-xs text-text-secondary">{definition.description}</span></span>{definition.customerFacing ? <Badge tone="warning">Approval required</Badge> : null}</button><span className="grid shrink-0 gap-1"><button type="button" aria-label={`Move ${definition.label} up`} disabled={!canWrite || index === 0} onClick={() => move(index, index - 1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary disabled:opacity-40"><ChevronUp className="h-4 w-4" /></button><button type="button" aria-label={`Move ${definition.label} down`} disabled={!canWrite || index === nodes.length - 1} onClick={() => move(index, index + 1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary disabled:opacity-40"><ChevronDown className="h-4 w-4" /></button></span></li>; })}</ol>}
      </section>

        <aside className="border-t border-border p-4 xl:border-l xl:border-t-0"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Inspector</h2>{active ? <><h3 className="mt-4 text-base font-semibold text-text-primary">{NODE_DEFINITIONS[active.kind].label}</h3><p className="mt-1 text-xs leading-relaxed text-text-secondary">{NODE_DEFINITIONS[active.kind].description}</p><NodeInspector node={active} tags={tags.data ?? []} campaigns={campaigns.data ?? []} onChange={(changed) => setNodes((current) => current.map((node) => node.id === changed.id ? changed : node))} onRemove={() => { const next = nodes.filter((node) => node.id !== active.id); setNodes(next); setEdges(linearGraph(next).edges ?? []); setSelected(null); }} /></> : <p className="mt-4 text-sm text-text-secondary">Select a step to configure it.</p>}
        <div className="mt-6 border-t border-border pt-4"><Button variant="secondary" block leftIcon={<Play className="h-4 w-4" />} disabled={!canWrite || !flow.active_version_no || dirty || flow.has_unpublished_changes || busy} onClick={() => setTestOpen(true)}>Run test</Button><p className="mt-3 text-[11px] leading-relaxed text-text-disabled">Safe test mode uses the immutable version and records every step. Actions are simulated; no business record or customer message can change.</p></div>
        <div className="mt-6 border-t border-border pt-4"><div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Test runs</h3>{runs.isLoading || selectedRun.isFetching ? <Spinner /> : null}</div><div className="mt-3 space-y-2">{runs.data?.slice(0, 5).map((run) => <button key={run.id} type="button" onClick={() => setSelectedRunId(run.id)} aria-pressed={selectedRunId === run.id} className={`w-full rounded-xl border p-3 text-left ${selectedRunId === run.id ? "border-accent bg-accent-soft" : "border-border bg-surface-2"}`}><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-text-primary">Version {run.version_no}</span><Badge tone={run.status === "succeeded" ? "success" : run.status === "failed" ? "danger" : "info"}>{run.status}</Badge></div><p className="mt-1 text-[11px] text-text-secondary">{run.completed_steps}/{run.total_steps} steps · {new Date(run.created_at).toLocaleString()}</p></button>)}</div>{runs.data?.length === 0 ? <p className="mt-3 text-xs text-text-disabled">No test runs yet.</p> : null}{selectedRun.data ? <div className="mt-3 rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-text-primary">Run evidence</span><Badge tone={selectedRun.data.status === "succeeded" ? "success" : selectedRun.data.status === "failed" ? "danger" : "info"}>{selectedRun.data.status}</Badge></div><ol className="mt-2 space-y-1">{selectedRun.data.attempts.map((attempt) => <li key={attempt.id} className="flex items-center justify-between gap-2 text-[11px]"><span className="truncate text-text-secondary">{attempt.node_id}</span><span className={attempt.status === "succeeded" ? "text-success" : attempt.status === "failed" ? "text-danger" : "text-text-disabled"}>{attempt.status}</span></li>)}</ol>{selectedRun.data.status === "succeeded" ? <p className="mt-2 text-[11px] leading-relaxed text-text-disabled">Simulation complete. No live effect was applied.</p> : null}{selectedRun.data.error_detail ? <p className="mt-2 text-[11px] text-danger">{selectedRun.data.error_detail}</p> : null}</div> : null}</div>
        <div className="mt-6 border-t border-border pt-4"><div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Versions</h3>{versions.isLoading ? <Spinner /> : null}</div><div className="mt-3 space-y-2">{versions.data?.map((version) => <div key={version.id} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-text-primary">Version {version.version_no}</span>{flow.active_version_no === version.version_no ? <Badge tone="success">Active</Badge> : null}</div><p className="mt-1 text-[11px] text-text-secondary">{new Date(version.published_at).toLocaleString()}</p>{canWrite && flow.active_version_no !== version.version_no ? <Button className="mt-2" size="sm" variant="ghost" disabled={busy || dirty} leftIcon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => void restore.mutateAsync({ versionNo: version.version_no, rowVersion: flow.row_version })}>Restore to draft</Button> : null}</div>)}{versions.data?.length === 0 ? <p className="text-xs text-text-disabled">No published versions yet.</p> : null}</div></div>
        {canPublish && flow.active_version_no ? <div className="mt-4">{flow.status === "disabled" ? <Button block variant="secondary" disabled={busy || dirty} onClick={() => void enable.mutateAsync(flow.row_version)}>Enable definition</Button> : <Button block variant="secondary" disabled={busy || dirty} onClick={() => void disable.mutateAsync(flow.row_version)}>Disable definition</Button>}</div> : null}
      </aside>
    </div>
  </div>{testOpen ? <Modal title="Test automation" onClose={() => setTestOpen(false)}><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void startTestRun(); }}><div className="rounded-xl border border-accent/30 bg-accent-soft p-3 text-xs leading-relaxed text-accent">This uses the active immutable version. Every action is simulated and recorded; nothing is sent or changed.</div><label className="block text-sm font-medium text-text-secondary">Test data (JSON)<textarea autoFocus className={`${inputClass} min-h-40 py-2 font-mono text-xs`} value={testInput} onChange={(event) => { setTestInput(event.target.value); setTestInputError(null); }} spellCheck={false} /></label>{testInputError ? <p role="alert" className="text-sm text-danger">{testInputError}</p> : null}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setTestOpen(false)}>Cancel</Button><Button type="submit" loading={runTest.isPending} leftIcon={<Play className="h-4 w-4" />}>Run safe test</Button></div></form></Modal> : null}</>;
}
