import { Bell, CheckCircle2, ChevronDown, ChevronUp, Clock3, GitBranch, GripVertical, Megaphone, Send, Tags, Trash2, UserRound, Webhook, Zap } from "lucide-react";
import { useState } from "react";

import { Badge, EmptyState } from "@/components/ui";

type NodeKind = "trigger" | "condition" | "action" | "delay" | "tag" | "assignment" | "wait" | "webhook" | "campaign" | "notification" | "approval";
interface BlueprintNode { id: number; kind: NodeKind }

const NODE_DEFINITIONS: Record<NodeKind, { label: string; description: string; icon: typeof Zap; customerFacing?: boolean }> = {
  trigger: { label: "Trigger", description: "Start from a governed domain event or schedule.", icon: Zap },
  condition: { label: "Condition", description: "Branch using verified event or CRM values.", icon: GitBranch },
  action: { label: "Internal action", description: "Create a safe internal task or state recommendation.", icon: CheckCircle2 },
  delay: { label: "Delay", description: "Pause for a configured duration.", icon: Clock3 },
  tag: { label: "Tag", description: "Apply an existing CRM tag through its service.", icon: Tags },
  assignment: { label: "Assignment", description: "Route work through the existing assignment authority.", icon: UserRound },
  wait: { label: "Wait for event", description: "Resume when a matching verified event arrives.", icon: Clock3 },
  webhook: { label: "Webhook", description: "Call a future governed outbound integration.", icon: Webhook },
  campaign: { label: "Campaign", description: "Prepare a campaign proposal; launch remains human-controlled.", icon: Megaphone, customerFacing: true },
  notification: { label: "Notification", description: "Notify an operator through the future notification contract.", icon: Bell },
  approval: { label: "Human approval", description: "Mandatory gate before every customer-facing effect.", icon: Send, customerFacing: true },
};

/** Interactive blueprint editor only; no workflow is persisted or executed without a domain runtime. */
export function AutomationBuilder(): JSX.Element {
  const [nodes, setNodes] = useState<BlueprintNode[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [nextId, setNextId] = useState(1);

  function add(kind: NodeKind): void {
    setNodes((current) => [...current, { id: nextId, kind }]);
    setSelected(nextId);
    setNextId((value) => value + 1);
  }
  function move(from: number, to: number): void {
    if (from === to) return;
    setNodes((current) => { const next = [...current]; const [item] = next.splice(from, 1); if (item) next.splice(to, 0, item); return next; });
  }
  const active = nodes.find((node) => node.id === selected);

  return <div className="grid min-h-[36rem] overflow-hidden rounded-2xl border border-border bg-surface shadow-sm xl:grid-cols-[15rem_minmax(0,1fr)_18rem]">
    <aside className="border-b border-border p-3 xl:border-b-0 xl:border-r"><h2 className="px-2 text-xs font-semibold uppercase tracking-wide text-text-disabled">Node library</h2><div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-1">{(Object.keys(NODE_DEFINITIONS) as NodeKind[]).map((kind) => { const definition=NODE_DEFINITIONS[kind]; const Icon=definition.icon; return <button key={kind} type="button" onClick={() => add(kind)} className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 text-left text-xs font-semibold text-text-primary hover:border-accent hover:bg-accent-soft"><Icon aria-hidden className="h-4 w-4 text-accent" />{definition.label}</button>; })}</div></aside>

    <section aria-label="Automation blueprint canvas" className="min-w-0 bg-[radial-gradient(circle_at_top,var(--color-accent-soft),transparent_44%)] p-4 sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-text-primary">Blueprint canvas</h2><p className="mt-1 text-xs text-text-secondary">Add and reorder nodes to explore the governed workflow shape.</p></div><Badge tone="info">Design only · not saved</Badge></div>
      {nodes.length === 0 ? <div className="flex min-h-[26rem] items-center justify-center"><EmptyState title="Start with a trigger" description="Choose a node from the library. Nothing can run or send from this blueprint." /></div> : <ol className="mx-auto max-w-2xl space-y-3">{nodes.map((node,index) => { const definition=NODE_DEFINITIONS[node.kind]; const Icon=definition.icon; return <li key={node.id} draggable onDragStart={() => setDragging(index)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (dragging !== null) move(dragging,index); setDragging(null); }} className="group flex items-center gap-2"><button type="button" onClick={() => setSelected(node.id)} aria-pressed={selected===node.id} className={`flex min-h-16 min-w-0 flex-1 items-center gap-3 rounded-2xl border bg-surface p-3 text-left shadow-sm transition ${selected===node.id ? "border-accent ring-2 ring-focus/30" : "border-border hover:border-accent"}`}><GripVertical aria-hidden className="h-4 w-4 text-text-disabled" /><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-5 w-5" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-text-primary">{index+1}. {definition.label}</span><span className="mt-0.5 block text-xs text-text-secondary">{definition.description}</span></span>{definition.customerFacing ? <Badge tone="warning">Approval required</Badge> : null}</button><span className="grid shrink-0 gap-1"><button type="button" aria-label={`Move ${definition.label} up`} disabled={index===0} onClick={() => move(index,index-1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"><ChevronUp aria-hidden className="h-4 w-4" /></button><button type="button" aria-label={`Move ${definition.label} down`} disabled={index===nodes.length-1} onClick={() => move(index,index+1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"><ChevronDown aria-hidden className="h-4 w-4" /></button></span></li>; })}</ol>}
    </section>

    <aside className="border-t border-border p-4 xl:border-l xl:border-t-0"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Inspector</h2>{active ? <div className="mt-4"><h3 className="text-base font-semibold text-text-primary">{NODE_DEFINITIONS[active.kind].label}</h3><p className="mt-2 text-sm leading-relaxed text-text-secondary">{NODE_DEFINITIONS[active.kind].description}</p><div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs leading-relaxed text-text-secondary">Configuration fields activate only with a versioned automation schema, permission policy, run ledger, retry/DLQ path, and approval API.</div><button type="button" onClick={() => { setNodes((current) => current.filter((node) => node.id !== active.id)); setSelected(null); }} className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-xl border border-danger/40 text-xs font-semibold text-danger hover:bg-danger-soft"><Trash2 aria-hidden className="h-4 w-4" />Remove node</button></div> : <p className="mt-4 text-sm text-text-secondary">Select a node to inspect its governed boundary.</p>}<div className="mt-6 border-t border-border pt-4"><button type="button" disabled title="Automation persistence is not in the current API contract" className="min-h-10 w-full rounded-xl bg-accent px-3 text-sm font-semibold text-accent-fg disabled:cursor-not-allowed disabled:opacity-50">Save automation</button><button type="button" disabled title="No workflow runtime is registered" className="mt-2 min-h-10 w-full rounded-xl border border-border text-sm font-semibold text-text-disabled disabled:cursor-not-allowed">Run test</button><p className="mt-3 text-[11px] leading-relaxed text-text-disabled">Fail-safe boundary: no node executes, schedules, mutates, calls a webhook, or sends a customer message.</p></div></aside>
  </div>;
}
