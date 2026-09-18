import {
  Bell, CheckCircle2, ChevronDown, ChevronUp, Clock3, GitBranch, GripVertical,
  MessageCircleMore, Megaphone, Play, RotateCcw, Save, Send, Tags, Trash2, UserRound,
  Webhook, Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge, Button, EmptyState, ErrorState, Modal, Spinner } from "@/components/ui";
import {
  apiErrorMessage, useAutomationRun, useAutomationRuns, useAutomationTriggerReceipts, useAutomationVersions,
  useCreateAutomationTestRun, useDisableAutomation, useEnableAutomation, usePublishAutomation,
  useRestoreAutomation, useUpdateAutomation, useValidateAutomation,
} from "@/features/automation/api";
import type { AutomationEdge, AutomationFlow, AutomationGraph, AutomationNode } from "@/features/automation/types";
import { graphEdges, graphNodes } from "@/features/automation/types";
import { useCampaigns, useTags } from "@/features/campaigns/api";
import { useAssignableUsers } from "@/features/inbox/api";
import type { UserSummary } from "@/features/inbox/types";
import { useHasPermission } from "@/lib/auth";
import { createIdempotencyKey } from "@/lib/idempotency";

type NodeKind = AutomationNode["kind"];

const NODE_DEFINITIONS: Record<NodeKind, { label: string; description: string; icon: typeof Zap; customerFacing?: boolean; liveEffect?: boolean }> = {
  trigger: { label: "Trigger", description: "Start from a verified event or schedule.", icon: Zap },
  condition: { label: "Condition", description: "Continue only when a verified value matches.", icon: GitBranch },
  action: { label: "Create task", description: "Create a tracked internal follow-up for this customer.", icon: CheckCircle2, liveEffect: true },
  handoff: { label: "Human handoff", description: "Place the current conversation in Live Chat Requested through the governed execution API.", icon: MessageCircleMore, liveEffect: true },
  delay: { label: "Delay", description: "Pause the live run for a bounded duration, then resume from its durable checkpoint.", icon: Clock3, liveEffect: true },
  tag: { label: "Apply tag", description: "Add an existing CRM tag to the triggering customer.", icon: Tags, liveEffect: true },
  remove_tag: { label: "Remove tag", description: "Remove an existing CRM tag from the triggering customer.", icon: Tags, liveEffect: true },
  assignment: { label: "Assignment", description: "Assign the triggering conversation to an inbox user or fair rotation.", icon: UserRound, liveEffect: true },
  wait: { label: "Wait for event", description: "Pause for this customer's next message, completed task, or a bounded timeout.", icon: Clock3, liveEffect: true },
  webhook: { label: "Webhook", description: "Reference a future governed outbound integration.", icon: Webhook },
  campaign: { label: "Campaign proposal", description: "Prepare a proposal; never launch directly.", icon: Megaphone, customerFacing: true },
  notification: { label: "Notification", description: "Notify the automation publisher in the internal Notification Center.", icon: Bell, liveEffect: true },
  approval: { label: "Human approval", description: "Mandatory gate before a customer-facing effect.", icon: Send, customerFacing: true },
};

const inputClass = "mt-1 min-h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-focus focus:ring-2 focus:ring-focus/20";
const NIL_UUID = "00000000-0000-0000-0000-000000000000";
const LIVE_CONDITION_FIELDS = [
  { value: "event_type", label: "Event type" },
  { value: "source", label: "Connector source" },
  { value: "payload.direction", label: "Message direction" },
  { value: "payload.message_type", label: "Message type" },
  { value: "payload.source", label: "Contact source" },
  { value: "payload.opt_in_status", label: "Contact opt-in status" },
  { value: "payload.previous_status", label: "Previous conversation status" },
  { value: "payload.inactive_after_hours", label: "Inactive threshold (hours)" },
  { value: "payload.from_stage", label: "Previous lead stage" },
  { value: "payload.to_stage", label: "New lead stage" },
] as const;
let nodeSequence = 0;
const AUTHORABLE_KINDS = (Object.keys(NODE_DEFINITIONS) as NodeKind[]).filter((kind) => kind !== "webhook");

interface EditorConfig {
  event?: string;
  schedule_cron?: string | null;
  field?: string;
  operator?: string;
  value?: unknown;
  title?: string;
  task_type?: string;
  priority?: string;
  due_in_minutes?: number;
  reason?: string;
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
    condition: { field: "payload.message_type", operator: "eq", value: "text" },
    action: { action: "create_task", title: "Follow up with customer", task_type: "custom", priority: "medium", due_in_minutes: 1440 },
    handoff: { reason: "Customer requested a human agent" },
    delay: { seconds: 3600 },
    tag: { tag_id: NIL_UUID },
    remove_tag: { tag_id: NIL_UUID },
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

const TERMINAL_BRANCH_KINDS = new Set<NodeKind>([
  "action", "handoff", "tag", "remove_tag", "assignment", "notification",
]);
const BRANCH_EFFECT_KINDS = Array.from(TERMINAL_BRANCH_KINDS);
const MAX_BRANCH_STEPS = 2;

interface BoundedBranch {
  conditionId: string;
  yesTargetIds: string[];
  noTargetIds: string[];
  sharedDelayId: string | null;
  sharedTargetId: string | null;
}

function boundedBranch(nodes: AutomationNode[], edges: AutomationEdge[]): BoundedBranch | null {
  if (nodes.length < 4 || nodes.length > 7 || ![nodes.length - 1, nodes.length].includes(edges.length)) return null;
  const trigger = nodes.find((node) => node.kind === "trigger");
  const condition = nodes.find((node) => node.kind === "condition");
  if (!trigger || !condition) return null;
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  const outgoing = new Map(nodes.map((node) => [node.id, [] as AutomationEdge[]]));
  for (const edge of edges) {
    if (!incoming.has(edge.target) || !outgoing.has(edge.source)) return null;
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    outgoing.get(edge.source)?.push(edge);
  }
  if (Array.from(incoming.values()).some((count) => count > 2)) return null;
  const triggerEdges = outgoing.get(trigger.id) ?? [];
  const conditionEdges = outgoing.get(condition.id) ?? [];
  if (
    triggerEdges.length !== 1
    || triggerEdges[0]?.target !== condition.id
    || triggerEdges[0]?.label?.trim()
    || incoming.get(trigger.id) !== 0
    || incoming.get(condition.id) !== 1
    || conditionEdges.length !== 2
  ) return null;
  const yes = conditionEdges.find((edge) => edge.label?.trim().toLowerCase() === "yes");
  const no = conditionEdges.find((edge) => edge.label?.trim().toLowerCase() === "no");
  if (!yes || !no || yes.target === no.target) return null;

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const mergeIds = nodes.filter((node) => incoming.get(node.id) === 2).map((node) => node.id);
  if (mergeIds.length > 1) return null;
  const mergeId = mergeIds[0] ?? null;
  let sharedDelayId: string | null = null;
  let sharedTargetId: string | null = null;
  if (mergeId) {
    const mergeNode = nodeById.get(mergeId);
    const mergeEdges = outgoing.get(mergeId) ?? [];
    if (mergeNode?.kind === "delay") {
      const sharedEdge = mergeEdges[0];
      const sharedNode = sharedEdge ? nodeById.get(sharedEdge.target) : null;
      if (
        mergeEdges.length !== 1
        || sharedEdge?.label?.trim()
        || !sharedNode
        || incoming.get(sharedNode.id) !== 1
        || !TERMINAL_BRANCH_KINDS.has(sharedNode.kind)
        || (outgoing.get(sharedNode.id)?.length ?? 0) > 0
      ) return null;
      sharedDelayId = mergeId;
      sharedTargetId = sharedNode.id;
    } else {
      if (!mergeNode || !TERMINAL_BRANCH_KINDS.has(mergeNode.kind) || mergeEdges.length > 0) return null;
      sharedTargetId = mergeId;
    }
  }
  const delayNodes = nodes.filter((node) => node.kind === "delay");
  if (delayNodes.length > 1 || (delayNodes.length === 1 && delayNodes[0]?.id !== sharedDelayId)) return null;
  const sharedNode = sharedTargetId ? nodeById.get(sharedTargetId) : null;
  const branchNodeIds = new Set<string>();
  const orderedBranch = (firstId: string): { nodeIds: string[]; reachesShared: boolean } | null => {
    const ordered: string[] = [];
    let reachesShared = false;
    let current = firstId;
    while (true) {
      const node = nodeById.get(current);
      if (!node || branchNodeIds.has(current) || !TERMINAL_BRANCH_KINDS.has(node.kind)) return null;
      branchNodeIds.add(current);
      ordered.push(current);
      if (ordered.length > MAX_BRANCH_STEPS) return null;
      const currentEdges = outgoing.get(current) ?? [];
      if (currentEdges.length === 0) break;
      if (currentEdges.length !== 1 || currentEdges[0]?.label?.trim()) return null;
      const nextId = currentEdges[0]?.target;
      if (mergeId && nextId === mergeId) {
        reachesShared = true;
        break;
      }
      if (!nextId || incoming.get(nextId) !== 1) return null;
      current = nextId;
    }
    const kinds = ordered.map((nodeId) => nodeById.get(nodeId)?.kind);
    if (sharedNode) kinds.push(sharedNode.kind);
    return kinds.length === new Set(kinds).size ? { nodeIds: ordered, reachesShared } : null;
  };
  const yesBranch = orderedBranch(yes.target);
  const noBranch = orderedBranch(no.target);
  const nonGateIds = nodes
    .filter((node) => node.id !== trigger.id && node.id !== condition.id)
    .map((node) => node.id);
  const expectedBranchIds = nonGateIds.filter(
    (nodeId) => nodeId !== sharedDelayId && nodeId !== sharedTargetId,
  );
  if (
    !yesBranch
    || !noBranch
    || yesBranch.reachesShared !== Boolean(mergeId)
    || noBranch.reachesShared !== Boolean(mergeId)
    || branchNodeIds.size !== expectedBranchIds.length
    || expectedBranchIds.some((nodeId) => !branchNodeIds.has(nodeId))
  ) return null;
  return {
    conditionId: condition.id,
    yesTargetIds: yesBranch.nodeIds,
    noTargetIds: noBranch.nodeIds,
    sharedDelayId,
    sharedTargetId,
  };
}

function NodeInspector({ node, onChange, onRemove, removeDisabled = false, tags, campaigns, users }: { node: AutomationNode; onChange: (node: AutomationNode) => void; onRemove: () => void; removeDisabled?: boolean; tags: { id: string; name: string }[]; campaigns: { id: string; name: string }[]; users: UserSummary[] }): JSX.Element {
  const setConfig = (config: object) => onChange({ ...node, config } as AutomationNode);
  const config = node.config as unknown as EditorConfig;
  return <div className="mt-4 space-y-4">
    <label className="block text-xs font-medium text-text-secondary">Step name<input className={inputClass} value={node.label ?? ""} onChange={(event) => onChange({ ...node, label: event.target.value } as AutomationNode)} /></label>
    {node.kind === "trigger" ? <><label className="block text-xs font-medium text-text-secondary">Event<select className={inputClass} value={config.event ?? "contact.created"} onChange={(event) => setConfig({ event: event.target.value, ...(event.target.value === "schedule" ? { schedule_cron: "0 9 * * 1-5" } : {}) })}><option value="contact.created">Contact created</option><option value="message.received">Message received</option><option value="conversation.auto_resolved">Conversation auto-resolved</option><option value="lead.stage_changed">Lead stage changed</option><option value="schedule">Schedule</option></select></label>{config.event === "schedule" ? <><label className="block text-xs font-medium text-text-secondary">Five-field cron schedule<input className={inputClass} value={config.schedule_cron ?? ""} onChange={(event) => setConfig({ ...config, schedule_cron: event.target.value })} /></label><p className="text-[11px] leading-relaxed text-text-disabled">Runs in the organization timezone. Live Schedule supports one internal Notification and an optional durable Delay; it never sends a customer message.</p></> : null}<p className="text-[11px] leading-relaxed text-text-disabled">Message received supports all proven Inbox/internal effects. Contact created supports tag changes and internal Notification. Conversation auto-resolved and Lead stage changed support safe internal follow-up Tasks, tag changes and internal Notification. Event paths support one event-safe Condition, one durable Delay, and one bounded Wait for the same customer&apos;s next message, completed Task or lead-stage change before a later effect. Schedule supports internal Notification with optional Delay.</p></> : null}
    {node.kind === "condition" ? <><label className="block text-xs font-medium text-text-secondary">Field<input className={inputClass} list="automation-live-condition-fields" value={config.field ?? ""} onChange={(event) => setConfig({ ...config, field: event.target.value })} /><datalist id="automation-live-condition-fields">{LIVE_CONDITION_FIELDS.map((field) => <option key={field.value} value={field.value}>{field.label}</option>)}</datalist></label><label className="block text-xs font-medium text-text-secondary">Operator<select className={inputClass} value={config.operator ?? "eq"} onChange={(event) => setConfig({ ...config, operator: event.target.value })}>{["eq", "ne", "contains", "exists", "gt", "gte", "lt", "lte"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>{config.operator !== "exists" ? <label className="block text-xs font-medium text-text-secondary">Value<input className={inputClass} value={typeof config.value === "string" ? config.value : String(config.value ?? "")} onChange={(event) => setConfig({ ...config, value: event.target.value })} /></label> : null}<p className="text-[11px] leading-relaxed text-text-disabled">Live event decisions support the suggested metadata fields with eq, ne, contains, or exists. Build Trigger, Condition, one Yes action and one No action to enable a bounded branch, then optionally add one more distinct internal effect to either side and one shared follow-up with a durable Delay. Other fields, operators and larger branches fail closed.</p></> : null}
    {node.kind === "action" ? <><label className="block text-xs font-medium text-text-secondary">Task title<input className={inputClass} value={config.title ?? ""} onChange={(event) => setConfig({ ...config, title: event.target.value })} /></label><label className="block text-xs font-medium text-text-secondary">Task type<select className={inputClass} value={config.task_type ?? "custom"} onChange={(event) => setConfig({ ...config, task_type: event.target.value })}><option value="custom">Custom</option><option value="call">Call</option><option value="whatsapp">WhatsApp</option><option value="collect_documents">Collect documents</option><option value="verification">Verification</option><option value="reminder">Reminder</option><option value="meeting">Meeting</option></select></label><label className="block text-xs font-medium text-text-secondary">Priority<select className={inputClass} value={config.priority ?? "medium"} onChange={(event) => setConfig({ ...config, priority: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label><label className="block text-xs font-medium text-text-secondary">Due in minutes<input className={inputClass} type="number" min={5} max={525600} value={config.due_in_minutes ?? 1440} onChange={(event) => setConfig({ ...config, due_in_minutes: Number(event.target.value) })} /></label><p className="text-[11px] leading-relaxed text-text-disabled">Live tasks are assigned to the active automation publisher and linked to the triggering customer. Conversation-backed events also retain their conversation link.</p></> : null}
    {node.kind === "handoff" ? <label className="block text-xs font-medium text-text-secondary">Handoff reason<input className={inputClass} value={config.reason ?? ""} onChange={(event) => setConfig({ reason: event.target.value })} /></label> : null}
    {node.kind === "delay" ? <><label className="block text-xs font-medium text-text-secondary">Delay (seconds)<input className={inputClass} type="number" min={60} max={2592000} value={config.seconds ?? 60} onChange={(event) => setConfig({ seconds: Number(event.target.value) })} /></label><p className="text-[11px] leading-relaxed text-text-disabled">One live delay can pause a connected inbound run for 1 minute to 30 days. Completed steps stay checkpointed, and the next step cannot execute before the scheduled resume.</p></> : null}
    {node.kind === "tag" ? <><label className="block text-xs font-medium text-text-secondary">Tag<select className={inputClass} value={config.tag_id ?? NIL_UUID} onChange={(event) => setConfig({ tag_id: event.target.value })}><option value={NIL_UUID}>Choose a tag</option>{tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select></label><p className="text-[11px] leading-relaxed text-text-disabled">Live inbound runs apply this existing CRM tag once to the triggering customer. An already-present tag completes safely without duplicate timeline or audit evidence.</p></> : null}
    {node.kind === "remove_tag" ? <><label className="block text-xs font-medium text-text-secondary">Tag<select className={inputClass} value={config.tag_id ?? NIL_UUID} onChange={(event) => setConfig({ tag_id: event.target.value })}><option value={NIL_UUID}>Choose a tag</option>{tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select></label><p className="text-[11px] leading-relaxed text-text-disabled">Live inbound runs remove this existing CRM tag from the triggering customer. An already-absent tag completes safely without duplicate timeline or audit evidence.</p></> : null}
    {node.kind === "assignment" ? <><label className="block text-xs font-medium text-text-secondary">Routing<select className={inputClass} value={config.mode ?? "round_robin"} onChange={(event) => setConfig(event.target.value === "user" ? { mode: "user", user_id: users[0]?.id ?? NIL_UUID } : { mode: "round_robin", user_id: null })}><option value="round_robin">Round robin</option><option value="user">Specific user</option></select></label>{config.mode === "user" ? <label className="block text-xs font-medium text-text-secondary">Assignee<select className={inputClass} value={config.user_id ?? NIL_UUID} onChange={(event) => setConfig({ mode: "user", user_id: event.target.value })}><option value={NIL_UUID}>Choose an active user</option>{config.user_id && config.user_id !== NIL_UUID && !users.some((user) => user.id === config.user_id) ? <option value={config.user_id}>Configured user</option> : null}{users.map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}</select></label> : null}<p className="text-[11px] leading-relaxed text-text-disabled">Live inbound runs never replace an existing owner. Round robin rotates eligible inbox members per automation; a specific user must still be active with inbox access when the run executes.</p></> : null}
    {node.kind === "wait" ? <><label className="block text-xs font-medium text-text-secondary">Resume event<select className={inputClass} value={config.event ?? "message.received"} onChange={(event) => setConfig({ ...config, event: event.target.value })}><option value="message.received">Message received</option><option value="lead.stage_changed">Lead stage changed</option><option value="task.completed">Task completed</option></select></label><label className="block text-xs font-medium text-text-secondary">Timeout (seconds)<input className={inputClass} type="number" min={60} max={2592000} value={config.timeout_seconds ?? ""} onChange={(event) => setConfig({ ...config, timeout_seconds: Number(event.target.value) })} /></label><p className="text-[11px] leading-relaxed text-text-disabled">One live Wait can resume on the same customer&apos;s future Message received, Task completed or Lead stage changed fact, or continue after a required 1 minute to 30 day timeout. Put at least one internal effect after it.</p></> : null}
    {node.kind === "webhook" ? <label className="block text-xs font-medium text-text-secondary">Governed webhook ID<input className={inputClass} value={config.webhook_id ?? ""} onChange={(event) => setConfig({ webhook_id: event.target.value })} /></label> : null}
    {node.kind === "campaign" ? <label className="block text-xs font-medium text-text-secondary">Campaign<select className={inputClass} value={config.campaign_id ?? NIL_UUID} onChange={(event) => setConfig({ campaign_id: event.target.value })}><option value={NIL_UUID}>Choose a campaign</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></label> : null}
    {node.kind === "notification" ? <><label className="block text-xs font-medium text-text-secondary">Internal message<textarea className={`${inputClass} min-h-24 py-2`} value={config.message ?? ""} onChange={(event) => setConfig({ message: event.target.value })} /></label><p className="text-[11px] leading-relaxed text-text-disabled">Live runs deliver this once to the active automation publisher in the existing Notification Center. Event triggers link to their customer; Schedule notifications are workspace-only. No email, browser push, or customer message is sent.</p></> : null}
    {node.kind === "approval" ? <label className="block text-xs font-medium text-text-secondary">Required permission<select className={inputClass} value={config.permission ?? "campaigns:send"} onChange={(event) => setConfig({ permission: event.target.value })}><option value="campaigns:send">Campaign send</option><option value="messages:send">Message send</option></select></label> : null}
    <Button variant="secondary" block disabled={removeDisabled} leftIcon={<Trash2 className="h-4 w-4 text-danger" />} onClick={onRemove}>Remove step</Button>
    {removeDisabled ? <p className="text-[11px] leading-relaxed text-text-disabled">Return to a linear gate before removing a branch root. A second branch step, shared delay or shared follow-up can be removed directly.</p> : null}
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
  const receipts = useAutomationTriggerReceipts(flow.id);
  const selectedRun = useAutomationRun(selectedRunId);
  const runTest = useCreateAutomationTestRun(flow.id);
  const canReadTags = useHasPermission("contacts:read");
  const canReadCampaigns = useHasPermission("campaigns:read");
  const canReadUsers = useHasPermission("users:read");
  const tags = useTags(canReadTags);
  const campaigns = useCampaigns(canReadCampaigns);
  const users = useAssignableUsers(canReadUsers);

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
  const branch = useMemo(() => boundedBranch(nodes, edges), [nodes, edges]);
  const branchCandidate = nodes.length === 4
    && nodes[0]?.kind === "trigger"
    && nodes[1]?.kind === "condition"
    && TERMINAL_BRANCH_KINDS.has(nodes[2]?.kind as NodeKind)
    && TERMINAL_BRANCH_KINDS.has(nodes[3]?.kind as NodeKind);
  const dirty = name !== flow.name || description !== (flow.description ?? "") || JSON.stringify(graph) !== JSON.stringify({ nodes: flow.graph.nodes ?? [], edges: flow.graph.edges ?? [] });
  const active = nodes.find((node) => node.id === selected) ?? null;
  const busy = update.isPending || publish.isPending || disable.isPending || enable.isPending || restore.isPending || runTest.isPending;
  const error = update.error ?? validate.error ?? publish.error ?? disable.error ?? enable.error ?? restore.error ?? runTest.error;

  function add(kind: NodeKind): void {
    let node = createNode(kind);
    if ((kind === "tag" || kind === "remove_tag") && tags.data?.[0]) node = { ...node, config: { tag_id: tags.data[0].id } } as AutomationNode;
    if (kind === "campaign" && campaigns.data?.[0]) node = { ...node, config: { campaign_id: campaigns.data[0].id } } as AutomationNode;
    const next = [...nodes, node]; setNodes(next); setEdges(linearGraph(next).edges ?? []); setSelected(node.id); setNotice(null);
  }
  function move(from: number, to: number): void {
    if (from === to) return;
    const next = [...nodes]; const [item] = next.splice(from, 1); if (item) next.splice(to, 0, item); setNodes(next); setEdges(linearGraph(next).edges ?? []);
  }
  function addBranchStep(kind: NodeKind, outcome: "yes" | "no"): void {
    if (!branch || !TERMINAL_BRANCH_KINDS.has(kind)) return;
    const branchIds = outcome === "yes" ? branch.yesTargetIds : branch.noTargetIds;
    const sharedKind = nodes.find((node) => node.id === branch.sharedTargetId)?.kind;
    const totalEffects = branch.yesTargetIds.length + branch.noTargetIds.length + (branch.sharedTargetId ? 1 : 0);
    if (
      totalEffects >= 4
      || branchIds.length >= MAX_BRANCH_STEPS
      || branchIds.some((nodeId) => nodes.find((node) => node.id === nodeId)?.kind === kind)
      || sharedKind === kind
    ) return;
    let node = createNode(kind);
    if ((kind === "tag" || kind === "remove_tag") && tags.data?.[0]) node = { ...node, config: { tag_id: tags.data[0].id } } as AutomationNode;
    const previousId = branchIds.at(-1);
    if (!previousId) return;
    const insertAt = nodes.findIndex((current) => current.id === previousId) + 1;
    const nextNodes = [...nodes];
    nextNodes.splice(insertAt, 0, node);
    setNodes(nextNodes);
    const sharedEntryId = branch.sharedDelayId ?? branch.sharedTargetId;
    const retainedEdges = sharedEntryId
      ? edges.filter((edge) => !(edge.source === previousId && edge.target === sharedEntryId))
      : edges;
    setEdges([
      ...retainedEdges,
      { id: `edge-${outcome}-${node.id}`, source: previousId, target: node.id },
      ...(sharedEntryId ? [{ id: `edge-${outcome}-shared-${node.id}`, source: node.id, target: sharedEntryId }] : []),
    ]);
    setSelected(node.id);
    setNotice(`Added a second ordered ${outcome === "yes" ? "Yes" : "No"} branch effect.`);
  }
  function addSharedBranchStep(kind: NodeKind): void {
    if (!branch || branch.sharedTargetId || !TERMINAL_BRANCH_KINDS.has(kind)) return;
    const branchKinds = [...branch.yesTargetIds, ...branch.noTargetIds]
      .map((nodeId) => nodes.find((node) => node.id === nodeId)?.kind);
    const totalEffects = branch.yesTargetIds.length + branch.noTargetIds.length;
    if (totalEffects >= 4 || branchKinds.includes(kind)) return;
    let node = createNode(kind);
    if ((kind === "tag" || kind === "remove_tag") && tags.data?.[0]) node = { ...node, config: { tag_id: tags.data[0].id } } as AutomationNode;
    const yesLastId = branch.yesTargetIds.at(-1);
    const noLastId = branch.noTargetIds.at(-1);
    if (!yesLastId || !noLastId) return;
    setNodes([...nodes, node]);
    setEdges([
      ...edges,
      { id: `edge-yes-shared-${node.id}`, source: yesLastId, target: node.id },
      { id: `edge-no-shared-${node.id}`, source: noLastId, target: node.id },
    ]);
    setSelected(node.id);
    setNotice("Added one shared follow-up after both branch outcomes.");
  }
  function addSharedBranchDelay(): void {
    if (!branch?.sharedTargetId || branch.sharedDelayId) return;
    const yesLastId = branch.yesTargetIds.at(-1);
    const noLastId = branch.noTargetIds.at(-1);
    if (!yesLastId || !noLastId) return;
    const node = createNode("delay");
    const sharedIndex = nodes.findIndex((current) => current.id === branch.sharedTargetId);
    if (sharedIndex < 0) return;
    const nextNodes = [...nodes];
    nextNodes.splice(sharedIndex, 0, node);
    setNodes(nextNodes);
    setEdges([
      ...edges.filter((edge) => !(
        edge.target === branch.sharedTargetId
        && (edge.source === yesLastId || edge.source === noLastId)
      )),
      { id: `edge-yes-delay-${node.id}`, source: yesLastId, target: node.id },
      { id: `edge-no-delay-${node.id}`, source: noLastId, target: node.id },
      { id: `edge-delay-shared-${node.id}`, source: node.id, target: branch.sharedTargetId },
    ]);
    setSelected(node.id);
    setNotice("Added one durable shared delay before the follow-up.");
  }
  function enableBranch(): void {
    if (!branchCandidate) return;
    const [trigger, condition, yesTarget, noTarget] = nodes;
    if (!trigger || !condition || !yesTarget || !noTarget) return;
    setEdges([
      { id: `edge-trigger-${condition.id}`, source: trigger.id, target: condition.id },
      { id: `edge-yes-${yesTarget.id}`, source: condition.id, target: yesTarget.id, label: "yes" },
      { id: `edge-no-${noTarget.id}`, source: condition.id, target: noTarget.id, label: "no" },
    ]);
    setNotice("Bounded Yes/No branch enabled. The third step is Yes; the fourth is No.");
  }
  function disableBranch(): void {
    setEdges(linearGraph(nodes).edges ?? []);
    setNotice("Returned to a linear condition gate.");
  }
  function removeStep(nodeId: string): void {
    if (branch) {
      if (branch.sharedDelayId === nodeId && branch.sharedTargetId) {
        const yesLastId = branch.yesTargetIds.at(-1);
        const noLastId = branch.noTargetIds.at(-1);
        if (!yesLastId || !noLastId) return;
        setNodes(nodes.filter((node) => node.id !== nodeId));
        setEdges([
          ...edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId),
          { id: `edge-yes-shared-${branch.sharedTargetId}`, source: yesLastId, target: branch.sharedTargetId },
          { id: `edge-no-shared-${branch.sharedTargetId}`, source: noLastId, target: branch.sharedTargetId },
        ]);
        setSelected(null);
        setNotice("Removed the shared delay; the follow-up still runs after either outcome.");
        return;
      }
      if (branch.sharedTargetId === nodeId) {
        const removedIds = new Set([nodeId, ...(branch.sharedDelayId ? [branch.sharedDelayId] : [])]);
        setNodes(nodes.filter((node) => !removedIds.has(node.id)));
        setEdges(edges.filter((edge) => !removedIds.has(edge.source) && !removedIds.has(edge.target)));
        setSelected(null);
        setNotice(branch.sharedDelayId ? "Removed the shared delay and follow-up; both branch bodies remain active." : "Removed the shared follow-up; both branch bodies remain active.");
        return;
      }
      const branchIds = branch.yesTargetIds.includes(nodeId)
        ? branch.yesTargetIds
        : branch.noTargetIds.includes(nodeId)
          ? branch.noTargetIds
          : [];
      if (branchIds.length <= 1 || branchIds.at(-1) !== nodeId) return;
      setNodes(nodes.filter((node) => node.id !== nodeId));
      const retainedEdges = edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
      const previousId = branchIds.at(-2);
      const sharedEntryId = branch.sharedDelayId ?? branch.sharedTargetId;
      setEdges(
        sharedEntryId && previousId
          ? [...retainedEdges, { id: `edge-restored-shared-${previousId}`, source: previousId, target: sharedEntryId }]
          : retainedEdges,
      );
      setSelected(null);
      setNotice("Removed the second branch effect; the bounded split remains active.");
      return;
    }
    const next = nodes.filter((node) => node.id !== nodeId);
    setNodes(next);
    setEdges(linearGraph(next).edges ?? []);
    setSelected(null);
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
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-secondary"><Badge tone={flow.status === "published" ? "success" : flow.status === "disabled" ? "warning" : "neutral"}>{flow.status}</Badge>{flow.active_version_no ? <span>Active version {flow.active_version_no}</span> : <span>Not published</span>}{flow.next_run_at && !flow.has_unpublished_changes ? <span>Next scheduled live run {new Date(flow.next_run_at).toLocaleString()}</span> : flow.next_run_at ? <span>Scheduled live run paused until this draft is published</span> : null}{dirty ? <Badge tone="warning">Unsaved changes</Badge> : flow.has_unpublished_changes ? <Badge tone="info">Draft changes ready</Badge> : null}</div>
    </section>

    {error ? <ErrorState message={apiErrorMessage(error)} /> : null}
    {notice ? <div role="status" className="rounded-xl border border-accent/30 bg-accent-soft px-4 py-3 text-sm text-accent">{notice}</div> : null}
    {validate.data && !validate.data.valid ? <div role="alert" className="rounded-xl border border-warning/40 bg-warning-soft p-4"><p className="text-sm font-semibold text-warning">Publication checks need attention</p><ul className="mt-2 space-y-1 text-xs text-text-secondary">{validate.data.issues.map((issue, index) => <li key={`${issue.code}-${issue.node_id ?? index}`}>• {issue.message}</li>)}</ul></div> : null}

    <div className="grid min-h-[36rem] overflow-hidden rounded-2xl border border-border bg-surface shadow-sm xl:grid-cols-[15rem_minmax(0,1fr)_19rem]">
      <aside className="border-b border-border p-3 xl:border-b-0 xl:border-r">
        <h2 className="px-2 text-xs font-semibold uppercase tracking-wide text-text-disabled">{branch ? "Add branch effect" : "Add a step"}</h2>
        {branch ? <div className="mt-3 space-y-2">
          <div className="grid grid-cols-[minmax(0,1fr)_auto_auto_auto] gap-2 px-2 text-[10px] font-semibold uppercase tracking-wide text-text-disabled"><span>Effect</span><span>Yes</span><span>No</span><span>After</span></div>
          {BRANCH_EFFECT_KINDS.map((kind) => { const definition = NODE_DEFINITIONS[kind]; const Icon = definition.icon; const yesKinds = branch.yesTargetIds.map((nodeId) => nodes.find((node) => node.id === nodeId)?.kind); const noKinds = branch.noTargetIds.map((nodeId) => nodes.find((node) => node.id === nodeId)?.kind); const sharedKind = nodes.find((node) => node.id === branch.sharedTargetId)?.kind; const totalEffects = branch.yesTargetIds.length + branch.noTargetIds.length + (branch.sharedTargetId ? 1 : 0); return <div key={kind} className="grid grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-2 rounded-xl border border-border bg-surface-2 px-2 py-2"><span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-text-primary"><Icon aria-hidden className="h-4 w-4 shrink-0 text-accent" /><span className="truncate">{definition.label}</span></span><button type="button" aria-label={`Add ${definition.label} to Yes branch`} disabled={!canWrite || totalEffects >= 4 || branch.yesTargetIds.length >= MAX_BRANCH_STEPS || yesKinds.includes(kind) || sharedKind === kind} onClick={() => addBranchStep(kind, "yes")} className="min-h-8 rounded-lg border border-border px-2 text-[11px] font-semibold text-success disabled:opacity-35">+ Yes</button><button type="button" aria-label={`Add ${definition.label} to No branch`} disabled={!canWrite || totalEffects >= 4 || branch.noTargetIds.length >= MAX_BRANCH_STEPS || noKinds.includes(kind) || sharedKind === kind} onClick={() => addBranchStep(kind, "no")} className="min-h-8 rounded-lg border border-border px-2 text-[11px] font-semibold text-warning disabled:opacity-35">+ No</button><button type="button" aria-label={`Add ${definition.label} after both branches`} disabled={!canWrite || totalEffects >= 4 || Boolean(branch.sharedTargetId) || yesKinds.includes(kind) || noKinds.includes(kind)} onClick={() => addSharedBranchStep(kind)} className="min-h-8 rounded-lg border border-border px-2 text-[11px] font-semibold text-accent disabled:opacity-35">+ Both</button></div>; })}
          <button type="button" disabled={!canWrite || !branch.sharedTargetId || Boolean(branch.sharedDelayId)} onClick={addSharedBranchDelay} className="min-h-10 w-full rounded-xl border border-border bg-surface-2 px-3 text-xs font-semibold text-accent disabled:opacity-35">Add shared delay before follow-up</button>
        </div> : <div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-1">{AUTHORABLE_KINDS.map((kind) => { const definition = NODE_DEFINITIONS[kind]; const Icon = definition.icon; return <button key={kind} type="button" disabled={!canWrite} onClick={() => add(kind)} className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 text-left text-xs font-semibold text-text-primary hover:border-accent hover:bg-accent-soft disabled:opacity-50"><Icon aria-hidden className="h-4 w-4 text-accent" />{definition.label}</button>; })}</div>}
        <p className="mt-3 px-2 text-[11px] leading-relaxed text-text-disabled">Message received can run all six proven internal effects. Contact created can change tags or notify internally. Conversation auto-resolved and Lead stage changed can create a follow-up Task, change tags or notify internally. Event paths can use one Yes/No split with up to two ordered distinct effects per side and one shared follow-up under the four-effect ceiling. That shared follow-up may pause once with a durable Delay. Schedule can notify the publisher with one optional Delay. Arbitrary merges, branch-specific Delay/Wait, nested branches and external actions fail safely.</p>
      </aside>

      <section aria-label="Automation flow canvas" className="min-w-0 bg-[radial-gradient(circle_at_top,var(--color-accent-soft),transparent_44%)] p-4 sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-text-primary">Flow</h2><p className="mt-1 text-xs text-text-secondary">Build a clear sequence. Saving and publishing never executes it.</p></div><span className="flex flex-wrap items-center gap-2"><Badge tone="info">Versioned definition</Badge>{branch ? <Button size="sm" variant="secondary" disabled={!canWrite} onClick={disableBranch}>Use linear gate</Button> : <Button size="sm" variant="secondary" disabled={!canWrite || !branchCandidate} onClick={enableBranch}>Enable Yes/No branch</Button>}</span></div>{!branch && !branchCandidate ? <p className="mb-4 text-[11px] leading-relaxed text-text-disabled">For a live split, build exactly Trigger → Condition → Yes action → No action, then enable the branch.</p> : branch ? <p className="mb-4 text-[11px] leading-relaxed text-text-disabled">Each side runs in order with up to two distinct effects. One optional shared follow-up runs after either outcome and may have one durable Delay immediately before it; the total remains capped at four effects. Reordering stays locked until you return to a linear gate.</p> : null}
        {nodes.length === 0 ? <div className="flex min-h-[26rem] items-center justify-center"><EmptyState title="Start with a trigger" description="Add a trigger, then connect the conditions and actions your team needs." /></div> : <ol className="mx-auto max-w-2xl space-y-3">{nodes.map((node, index) => { const definition = NODE_DEFINITIONS[node.kind]; const Icon = definition.icon; const yesIndex = branch?.yesTargetIds.indexOf(node.id) ?? -1; const noIndex = branch?.noTargetIds.indexOf(node.id) ?? -1; const branchLabel = branch?.sharedDelayId === node.id ? "Shared delay" : branch?.sharedTargetId === node.id ? "After both" : yesIndex === 0 ? "Yes branch" : yesIndex > 0 ? `Yes step ${yesIndex + 1}` : noIndex === 0 ? "No branch" : noIndex > 0 ? `No step ${noIndex + 1}` : null; return <li key={node.id} draggable={canWrite && branch === null} onDragStart={() => setDragging(index)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (dragging !== null && branch === null) move(dragging, index); setDragging(null); }} className="group flex items-center gap-2"><button type="button" onClick={() => setSelected(node.id)} aria-pressed={selected === node.id} className={`flex min-h-16 min-w-0 flex-1 items-center gap-3 rounded-2xl border bg-surface p-3 text-left shadow-sm transition ${selected === node.id ? "border-accent ring-2 ring-focus/30" : "border-border hover:border-accent"}`}><GripVertical aria-hidden className="h-4 w-4 text-text-disabled" /><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-5 w-5" /></span><span className="min-w-0 flex-1"><span className="flex flex-wrap items-center gap-2 text-sm font-semibold text-text-primary">{index + 1}. {node.label || definition.label}{branchLabel ? <Badge tone={branchLabel.startsWith("Yes") ? "success" : branchLabel.startsWith("No") ? "warning" : "info"}>{branchLabel}</Badge> : null}</span><span className="mt-0.5 block text-xs text-text-secondary">{definition.description}</span></span>{definition.customerFacing ? <Badge tone="warning">Approval required</Badge> : definition.liveEffect ? <Badge tone="info">Live contract</Badge> : null}</button><span className="grid shrink-0 gap-1"><button type="button" aria-label={`Move ${definition.label} up`} disabled={!canWrite || branch !== null || index === 0} onClick={() => move(index, index - 1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary disabled:opacity-40"><ChevronUp className="h-4 w-4" /></button><button type="button" aria-label={`Move ${definition.label} down`} disabled={!canWrite || branch !== null || index === nodes.length - 1} onClick={() => move(index, index + 1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-text-secondary disabled:opacity-40"><ChevronDown className="h-4 w-4" /></button></span></li>; })}</ol>}
      </section>

        <aside className="border-t border-border p-4 xl:border-l xl:border-t-0"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Inspector</h2>{active ? <><h3 className="mt-4 text-base font-semibold text-text-primary">{NODE_DEFINITIONS[active.kind].label}</h3><p className="mt-1 text-xs leading-relaxed text-text-secondary">{NODE_DEFINITIONS[active.kind].description}</p><NodeInspector node={active} tags={tags.data ?? []} campaigns={campaigns.data ?? []} users={users.data ?? []} onChange={(changed) => setNodes((current) => current.map((node) => node.id === changed.id ? changed : node))} onRemove={() => removeStep(active.id)} removeDisabled={Boolean(branch && branch.sharedTargetId !== active.id && branch.sharedDelayId !== active.id && !((branch.yesTargetIds.length > 1 && branch.yesTargetIds.at(-1) === active.id) || (branch.noTargetIds.length > 1 && branch.noTargetIds.at(-1) === active.id)))} /></> : <p className="mt-4 text-sm text-text-secondary">Select a step to configure it.</p>}
        <div className="mt-6 border-t border-border pt-4"><Button variant="secondary" block leftIcon={<Play className="h-4 w-4" />} disabled={!canWrite || !flow.active_version_no || dirty || flow.has_unpublished_changes || busy} onClick={() => setTestOpen(true)}>Run test</Button><p className="mt-3 text-[11px] leading-relaxed text-text-disabled">Safe test mode uses the immutable version and records every step. Actions are simulated; no business record or customer message can change.</p></div>
        <div className="mt-6 border-t border-border pt-4"><div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Run history</h3>{runs.isLoading || selectedRun.isFetching ? <Spinner /> : null}</div><div className="mt-3 space-y-2">{runs.data?.slice(0, 5).map((run) => <button key={run.id} type="button" onClick={() => setSelectedRunId(run.id)} aria-pressed={selectedRunId === run.id} className={`w-full rounded-xl border p-3 text-left ${selectedRunId === run.id ? "border-accent bg-accent-soft" : "border-border bg-surface-2"}`}><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-text-primary">Version {run.version_no}</span><span className="flex items-center gap-1"><Badge tone={run.mode === "live" ? "warning" : "neutral"}>{run.mode}</Badge><Badge tone={run.status === "succeeded" ? "success" : run.status === "failed" ? "danger" : "info"}>{run.status}</Badge></span></div><p className="mt-1 text-[11px] text-text-secondary">{run.completed_steps}/{run.total_steps} steps · {new Date(run.created_at).toLocaleString()}</p></button>)}</div>{runs.data?.length === 0 ? <p className="mt-3 text-xs text-text-disabled">No runs yet.</p> : null}{selectedRun.data ? <div className="mt-3 rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-text-primary">Run evidence</span><Badge tone={selectedRun.data.status === "succeeded" ? "success" : selectedRun.data.status === "failed" ? "danger" : "info"}>{selectedRun.data.status}</Badge></div><ol className="mt-2 space-y-1">{selectedRun.data.attempts.map((attempt) => <li key={attempt.id} className="flex items-center justify-between gap-2 text-[11px]"><span className="truncate text-text-secondary">{attempt.node_id}</span><span className={attempt.status === "succeeded" ? "text-success" : attempt.status === "failed" ? "text-danger" : attempt.status === "skipped" ? "text-warning" : "text-text-disabled"}>{attempt.status}</span></li>)}</ol>{selectedRun.data.status === "succeeded" ? <p className="mt-2 text-[11px] leading-relaxed text-text-disabled">{selectedRun.data.mode === "live" ? selectedRun.data.attempts.some((attempt) => attempt.status === "skipped") ? "Live decision completed; every unselected branch step is recorded as skipped." : "Live action completed with durable step evidence." : "Simulation complete. No live effect was applied."}</p> : null}{selectedRun.data.error_detail ? <p className="mt-2 text-[11px] text-danger">{selectedRun.data.error_detail}</p> : null}</div> : null}</div>
        <div className="mt-6 border-t border-border pt-4"><div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Trigger receipts</h3>{receipts.isLoading ? <Spinner /> : null}</div><div className="mt-3 space-y-2">{receipts.data?.slice(0, 5).map((receipt) => <div key={receipt.id} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-text-primary">{receipt.event_type}</span><Badge tone={receipt.status === "processed" ? "success" : receipt.status === "failed" ? "danger" : "info"}>{receipt.status}</Badge></div><p className="mt-1 text-[11px] text-text-secondary">Version {receipt.version_no} · {receipt.source ?? "system"} · {new Date(receipt.occurred_at).toLocaleString()}</p></div>)}</div>{receipts.data?.length === 0 ? <p className="mt-3 text-xs text-text-disabled">No real trigger receipts yet.</p> : null}<p className="mt-3 text-[11px] leading-relaxed text-text-disabled">Message received, Contact created, Conversation auto-resolved, Lead stage changed and Schedule receipts are durably dispatched to their bounded live paths. Waiting event receipts resume from the same run after a matching customer message, completed Task, lead-stage change, or timeout. Incompatible effects and other event types fail safely.</p></div>
        <div className="mt-6 border-t border-border pt-4"><div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-disabled">Versions</h3>{versions.isLoading ? <Spinner /> : null}</div><div className="mt-3 space-y-2">{versions.data?.map((version) => <div key={version.id} className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-text-primary">Version {version.version_no}</span>{flow.active_version_no === version.version_no ? <Badge tone="success">Active</Badge> : null}</div><p className="mt-1 text-[11px] text-text-secondary">{new Date(version.published_at).toLocaleString()}</p>{canWrite && flow.active_version_no !== version.version_no ? <Button className="mt-2" size="sm" variant="ghost" disabled={busy || dirty} leftIcon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => restore.mutate({ versionNo: version.version_no, rowVersion: flow.row_version })}>Restore to draft</Button> : null}</div>)}{versions.data?.length === 0 ? <p className="text-xs text-text-disabled">No published versions yet.</p> : null}</div></div>
        {canPublish && flow.active_version_no ? <div className="mt-4">{flow.status === "disabled" ? <Button block variant="secondary" disabled={busy || dirty} onClick={() => enable.mutate(flow.row_version)}>Enable definition</Button> : <Button block variant="secondary" disabled={busy || dirty} onClick={() => disable.mutate(flow.row_version)}>Disable definition</Button>}</div> : null}
      </aside>
    </div>
  </div>{testOpen ? <Modal title="Test automation" onClose={() => setTestOpen(false)}><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void startTestRun(); }}><div className="rounded-xl border border-accent/30 bg-accent-soft p-3 text-xs leading-relaxed text-accent">This uses the active immutable version. Every action is simulated and recorded; nothing is sent or changed.</div><label className="block text-sm font-medium text-text-secondary">Test data (JSON)<textarea autoFocus className={`${inputClass} min-h-40 py-2 font-mono text-xs`} value={testInput} onChange={(event) => { setTestInput(event.target.value); setTestInputError(null); }} spellCheck={false} /></label>{testInputError ? <p role="alert" className="text-sm text-danger">{testInputError}</p> : null}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setTestOpen(false)}>Cancel</Button><Button type="submit" loading={runTest.isPending} leftIcon={<Play className="h-4 w-4" />}>Run safe test</Button></div></form></Modal> : null}</>;
}
