import {
  AlertTriangle,
  CheckCircle2,
  Columns3,
  FileCheck2,
  Filter,
  GripVertical,
  List,
  RefreshCw,
  Search,
  Users,
} from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";

import { Badge, Button, Card, EmptyState, ErrorState, Modal, Skeleton } from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import {
  apiErrorMessage,
  useReactivationPipeline,
  useTransitionReactivation,
} from "@/features/reactivation/api";
import { ReactivationCaseDrawer } from "@/features/reactivation/ReactivationCaseDrawer";
import {
  REACTIVATION_STAGE_LABELS,
  REACTIVATION_STAGES,
  stageIndex,
  type ReactivationCard,
  type ReactivationStage,
} from "@/features/reactivation/types";
import { useHasPermission } from "@/lib/auth";

export const REACTIVATION_STAGE_BLUEPRINT = REACTIVATION_STAGES.map(
  (stage) => REACTIVATION_STAGE_LABELS[stage],
);

type ViewMode = "board" | "list";

interface PendingMove {
  card: ReactivationCard;
  target: ReactivationStage;
}

export function ReactivationPipelineBoard(): JSX.Element {
  const [query, setQuery] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [view, setView] = useState<ViewMode>("board");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dropStage, setDropStage] = useState<ReactivationStage | null>(null);
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null);
  const [reason, setReason] = useState("");
  const deferredQuery = useDeferredValue(query.trim());
  const canTransition = useHasPermission("reactivation:transition");
  const canReadUsers = useHasPermission("users:read");
  const users = useUsers(canReadUsers);
  const pipeline = useReactivationPipeline({
    q: deferredQuery || undefined,
    owner_user_id: ownerId || undefined,
    limit: 200,
  });
  const transition = useTransitionReactivation();

  const cards = useMemo(() => pipeline.data?.data ?? [], [pipeline.data?.data]);
  const selected = cards.find((card) => card.id === selectedId) ?? null;
  const counts = useMemo(
    () => new Map((pipeline.data?.stage_counts ?? []).map((entry) => [entry.stage, entry.count])),
    [pipeline.data?.stage_counts],
  );
  const byStage = useMemo(() => {
    const result = new Map<ReactivationStage, ReactivationCard[]>();
    for (const stage of REACTIVATION_STAGES) result.set(stage, []);
    for (const card of cards) result.get(card.stage)?.push(card);
    return result;
  }, [cards]);

  const activeTotal = REACTIVATION_STAGES.filter(
    (stage) => !["completed", "not_eligible", "not_interested"].includes(stage),
  ).reduce((sum, stage) => sum + (counts.get(stage) ?? 0), 0);
  const completed = counts.get("completed") ?? 0;
  const closed = completed + (counts.get("not_eligible") ?? 0) + (counts.get("not_interested") ?? 0);
  const conversionRate = closed > 0 ? Math.round((completed / closed) * 100) : 0;
  const breached = cards.filter((card) => card.sla_status === "breached").length;

  function requestMove(card: ReactivationCard, target: ReactivationStage): void {
    if (!canTransition || !card.available_transitions.includes(target)) return;
    setPendingMove({ card, target });
    setReason("");
  }

  function confirmMove(): void {
    if (!pendingMove) return;
    const reasonRequired = ["not_eligible", "not_interested"].includes(pendingMove.target);
    if (reasonRequired && !reason.trim()) return;
    transition.mutate(
      { card: pendingMove.card, toStage: pendingMove.target, reason },
      {
        onSuccess: () => {
          setPendingMove(null);
          setReason("");
        },
      },
    );
  }

  function handleDrop(target: ReactivationStage): void {
    const card = cards.find((candidate) => candidate.id === draggingId);
    setDraggingId(null);
    setDropStage(null);
    if (card) requestMove(card, target);
  }

  if (pipeline.isLoading) return <PipelineLoading />;
  if (pipeline.isError) {
    return <ErrorState message={apiErrorMessage(pipeline.error)} onRetry={() => void pipeline.refetch()} />;
  }

  return (
    <div className="space-y-4">
      <section aria-label="Pipeline summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Users} label="Active pipeline" value={activeTotal} detail={`${pipeline.data?.total ?? 0} total cases`} />
        <Metric icon={CheckCircle2} label="Completed" value={completed} detail={`${conversionRate}% closed-case conversion`} tone="success" />
        <Metric icon={AlertTriangle} label="SLA breaches" value={breached} detail="Across visible governed cases" tone={breached > 0 ? "danger" : "neutral"} />
        <Metric icon={FileCheck2} label="Visible evidence" value={pipeline.data?.visible ?? 0} detail="Maximum 200 current cards" />
      </section>

      <Card className="p-3" padding={false}>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end">
          <label className="min-w-0 flex-1 text-xs font-semibold text-text-secondary">
            Search cases
            <span className="mt-1 flex h-10 items-center gap-2 rounded-lg border border-border bg-surface px-3 focus-within:border-accent focus-within:ring-2 focus-within:ring-focus/20">
              <Search aria-hidden className="h-4 w-4 text-text-disabled" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, mobile or Vi number" className="w-full bg-transparent text-sm text-text-primary outline-none placeholder:text-text-disabled" />
            </span>
          </label>
          <label className="text-xs font-semibold text-text-secondary xl:w-56">
            Owner
            <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} disabled={!canReadUsers} className="mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary disabled:opacity-60">
              <option value="">All owners</option>
              {(users.data?.data ?? []).filter((user) => user.is_active).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}
            </select>
          </label>
          <div className="flex items-center gap-2">
            <div className="grid grid-cols-2 rounded-lg border border-border bg-surface-2 p-1" aria-label="Pipeline view">
              <button type="button" aria-label="Kanban view" aria-pressed={view === "board"} onClick={() => setView("board")} className={`flex min-h-9 items-center gap-2 rounded-md px-3 text-xs font-semibold ${view === "board" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"}`}><Columns3 aria-hidden className="h-4 w-4" />Board</button>
              <button type="button" aria-label="List view" aria-pressed={view === "list"} onClick={() => setView("list")} className={`flex min-h-9 items-center gap-2 rounded-md px-3 text-xs font-semibold ${view === "list" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"}`}><List aria-hidden className="h-4 w-4" />List</button>
            </div>
            <Button variant="secondary" size="sm" leftIcon={<RefreshCw className={`h-4 w-4 ${pipeline.isFetching ? "animate-spin" : ""}`} />} onClick={() => void pipeline.refetch()}>Refresh</Button>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3 text-xs text-text-secondary">
          <span className="flex items-center gap-1.5"><Filter aria-hidden className="h-3.5 w-3.5" />{cards.length} visible of {pipeline.data?.total ?? cards.length}</span>
          <span className="hidden sm:inline">Drag a card or use Alt + arrow keys. The server validates every move.</span>
        </div>
      </Card>

      {cards.length === 0 ? (
        <Card><EmptyState icon={<Columns3 className="h-7 w-7" />} title={query || ownerId ? "No cases match these filters" : "No reactivation cases yet"} description={query || ownerId ? "Clear a filter or search another customer." : "Create a governed reactivation case from an existing contact to begin the pipeline."} /></Card>
      ) : view === "board" ? (
        <div className="flex snap-x gap-3 overflow-x-auto pb-4" aria-label="Reactivation pipeline stages">
          {REACTIVATION_STAGES.map((stage) => (
            <PipelineColumn
              key={stage}
              stage={stage}
              cards={byStage.get(stage) ?? []}
              total={counts.get(stage) ?? 0}
              draggingId={draggingId}
              activeDrop={dropStage === stage}
              canTransition={canTransition}
              onDragStart={setDraggingId}
              onDragEnd={() => { setDraggingId(null); setDropStage(null); }}
              onDragOver={() => setDropStage(stage)}
              onDrop={() => handleDrop(stage)}
              onOpen={(card) => setSelectedId(card.id)}
              onMove={requestMove}
            />
          ))}
        </div>
      ) : (
        <PipelineList cards={cards} onOpen={(card) => setSelectedId(card.id)} onMove={requestMove} canTransition={canTransition} />
      )}

      {selected ? <ReactivationCaseDrawer card={selected} onClose={() => setSelectedId(null)} onMove={requestMove} /> : null}

      {pendingMove ? (
        <Modal title={`Move to ${REACTIVATION_STAGE_LABELS[pendingMove.target]}`} onClose={() => setPendingMove(null)}>
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">Move <strong className="text-text-primary">{pendingMove.card.contact_name}</strong> from {REACTIVATION_STAGE_LABELS[pendingMove.card.stage]}? This writes immutable stage, audit and Customer Timeline evidence.</p>
            <label className="block text-xs font-semibold text-text-secondary">Reason{["not_eligible", "not_interested"].includes(pendingMove.target) ? " (required)" : " (optional)"}<textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} maxLength={2000} className="mt-1 w-full rounded-lg border border-border bg-surface p-3 text-sm text-text-primary outline-none focus:border-accent" /></label>
            {transition.error ? <ErrorState message={apiErrorMessage(transition.error)} /> : null}
            <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setPendingMove(null)}>Cancel</Button><Button disabled={transition.isPending || (["not_eligible", "not_interested"].includes(pendingMove.target) && !reason.trim())} onClick={confirmMove}>{transition.isPending ? "Moving…" : "Confirm move"}</Button></div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

function PipelineColumn({ stage, cards, total, draggingId, activeDrop, canTransition, onDragStart, onDragEnd, onDragOver, onDrop, onOpen, onMove }: { stage: ReactivationStage; cards: ReactivationCard[]; total: number; draggingId: string | null; activeDrop: boolean; canTransition: boolean; onDragStart: (id: string) => void; onDragEnd: () => void; onDragOver: () => void; onDrop: () => void; onOpen: (card: ReactivationCard) => void; onMove: (card: ReactivationCard, target: ReactivationStage) => void }): JSX.Element {
  const dragged = cards.find((card) => card.id === draggingId);
  return (
    <section
      className={`min-h-[26rem] w-[18rem] shrink-0 snap-start rounded-2xl border bg-surface-2 p-3 transition ${activeDrop && !dragged ? "border-accent ring-2 ring-focus/20" : "border-border"}`}
      aria-label={REACTIVATION_STAGE_LABELS[stage]}
      onDragOver={(event) => { event.preventDefault(); onDragOver(); }}
      onDrop={(event) => { event.preventDefault(); onDrop(); }}
    >
      <header className="mb-3 flex items-center justify-between gap-2"><div><h2 className="text-sm font-semibold text-text-primary">{REACTIVATION_STAGE_LABELS[stage]}</h2><p className="mt-0.5 text-[11px] text-text-disabled">{cards.length} loaded</p></div><Badge tone={["completed"].includes(stage) ? "success" : ["not_eligible", "not_interested"].includes(stage) ? "danger" : "neutral"}>{total}</Badge></header>
      <div className="space-y-2">
        {cards.map((card) => <PipelineCard key={card.id} card={card} canTransition={canTransition} dragging={draggingId === card.id} onDragStart={() => onDragStart(card.id)} onDragEnd={onDragEnd} onOpen={() => onOpen(card)} onMove={(target) => onMove(card, target)} />)}
        {cards.length === 0 ? <EmptyState compact title="No cases" description="Drop a permitted case here or move it with the keyboard." /> : null}
      </div>
    </section>
  );
}

function PipelineCard({ card, canTransition, dragging, onDragStart, onDragEnd, onOpen, onMove }: { card: ReactivationCard; canTransition: boolean; dragging: boolean; onDragStart: () => void; onDragEnd: () => void; onOpen: () => void; onMove: (target: ReactivationStage) => void }): JSX.Element {
  function keyboardMove(direction: -1 | 1): void {
    const current = stageIndex(card.stage);
    const ordered = card.available_transitions.slice().sort((a, b) => stageIndex(a) - stageIndex(b));
    const target = direction > 0 ? ordered.find((stage) => stageIndex(stage) > current) : ordered.slice().reverse().find((stage) => stageIndex(stage) < current);
    if (target) onMove(target);
  }
  return (
    <article
      tabIndex={0}
      draggable={canTransition}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onKeyDown={(event) => {
        if (event.key === "Enter") onOpen();
        if (canTransition && event.altKey && event.key === "ArrowRight") { event.preventDefault(); keyboardMove(1); }
        if (canTransition && event.altKey && event.key === "ArrowLeft") { event.preventDefault(); keyboardMove(-1); }
      }}
      className={`group rounded-xl border border-border bg-surface p-3 shadow-sm outline-none transition hover:border-accent focus-visible:ring-2 focus-visible:ring-focus ${canTransition ? "cursor-grab" : ""} ${dragging ? "opacity-50" : ""}`}
      aria-label={`${card.contact_name}, ${REACTIVATION_STAGE_LABELS[card.stage]}`}
    >
      <div className="flex items-start gap-2"><GripVertical aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-text-disabled" /><button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left"><span className="block truncate text-sm font-semibold text-text-primary group-hover:text-accent">{card.contact_name}</span><span className="mt-0.5 block text-xs text-text-secondary">{card.contact_phone}</span></button>{card.sla_status === "breached" ? <AlertTriangle aria-label="SLA breached" className="h-4 w-4 shrink-0 text-danger" /> : null}</div>
      <div className="mt-3 flex flex-wrap gap-1"><Badge tone={card.latest_eligibility_status === "eligible" ? "success" : card.latest_eligibility_status === "not_eligible" ? "danger" : "neutral"}>{card.latest_eligibility_status?.replaceAll("_", " ") ?? "Unchecked"}</Badge>{card.overdue_task_count > 0 ? <Badge tone="danger">{card.overdue_task_count} overdue</Badge> : card.open_task_count > 0 ? <Badge tone="info">{card.open_task_count} tasks</Badge> : null}</div>
      <dl className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-2 text-[11px]"><div><dt className="text-text-disabled">Owner</dt><dd className="truncate font-medium text-text-secondary">{card.owner_name ?? "Unassigned"}</dd></div><div><dt className="text-text-disabled">Documents</dt><dd className="font-medium text-text-secondary">{card.verified_document_count}/{card.document_count}</dd></div></dl>
    </article>
  );
}

function PipelineList({ cards, onOpen, onMove, canTransition }: { cards: ReactivationCard[]; onOpen: (card: ReactivationCard) => void; onMove: (card: ReactivationCard, stage: ReactivationStage) => void; canTransition: boolean }): JSX.Element {
  return (
    <Card className="overflow-hidden" padding={false}>
      <div className="hidden overflow-x-auto md:block"><table className="w-full border-collapse text-left text-sm"><thead className="bg-surface-2 text-xs uppercase tracking-wide text-text-secondary"><tr><th className="px-4 py-3">Customer</th><th className="px-4 py-3">Stage</th><th className="px-4 py-3">Owner</th><th className="px-4 py-3">Eligibility</th><th className="px-4 py-3">Tasks / SLA</th><th className="px-4 py-3">Action</th></tr></thead><tbody className="divide-y divide-border">{cards.map((card) => <tr key={card.id} className="hover:bg-hover"><td className="px-4 py-3"><button type="button" onClick={() => onOpen(card)} className="font-semibold text-text-primary hover:text-accent">{card.contact_name}</button><p className="mt-0.5 text-xs text-text-secondary">{card.contact_phone}</p></td><td className="px-4 py-3"><Badge>{REACTIVATION_STAGE_LABELS[card.stage]}</Badge></td><td className="px-4 py-3 text-text-secondary">{card.owner_name ?? "Unassigned"}</td><td className="px-4 py-3 capitalize text-text-secondary">{card.latest_eligibility_status?.replaceAll("_", " ") ?? "Not checked"}</td><td className="px-4 py-3"><span className={card.sla_status === "breached" ? "text-danger" : "text-text-secondary"}>{card.open_task_count} open · {card.sla_status.replaceAll("_", " ")}</span></td><td className="px-4 py-3"><select aria-label={`Move ${card.contact_name}`} disabled={!canTransition || card.available_transitions.length === 0} defaultValue="" onChange={(event) => { if (event.target.value) onMove(card, event.target.value as ReactivationStage); event.target.value = ""; }} className="h-9 rounded-lg border border-border bg-surface px-2 text-xs text-text-primary disabled:opacity-50"><option value="">Move…</option>{card.available_transitions.map((target) => <option key={target} value={target}>{REACTIVATION_STAGE_LABELS[target]}</option>)}</select></td></tr>)}</tbody></table></div>
      <div className="divide-y divide-border md:hidden">{cards.map((card) => <button key={card.id} type="button" onClick={() => onOpen(card)} className="flex min-h-16 w-full items-center justify-between gap-3 p-4 text-left hover:bg-hover"><span className="min-w-0"><span className="block truncate text-sm font-semibold text-text-primary">{card.contact_name}</span><span className="mt-1 block text-xs text-text-secondary">{REACTIVATION_STAGE_LABELS[card.stage]} · {card.owner_name ?? "Unassigned"}</span></span><Badge tone={card.sla_status === "breached" ? "danger" : "neutral"}>{card.open_task_count} tasks</Badge></button>)}</div>
    </Card>
  );
}

function Metric({ icon: Icon, label, value, detail, tone = "neutral" }: { icon: typeof Users; label: string; value: number; detail: string; tone?: "neutral" | "success" | "danger" }): JSX.Element {
  const toneClass = tone === "success" ? "bg-success/10 text-success" : tone === "danger" ? "bg-danger/10 text-danger" : "bg-accent-soft text-accent";
  return <Card className="flex items-center gap-3 p-4" padding={false}><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${toneClass}`}><Icon aria-hidden className="h-5 w-5" /></span><div className="min-w-0"><p className="text-xl font-bold text-text-primary">{value}</p><p className="text-xs font-semibold text-text-secondary">{label}</p><p className="mt-0.5 truncate text-[11px] text-text-disabled">{detail}</p></div></Card>;
}

function PipelineLoading(): JSX.Element {
  return <div aria-label="Loading reactivation pipeline" className="space-y-4"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-24 w-full" />)}</div><Skeleton className="h-28 w-full" /><div className="flex gap-3 overflow-hidden">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-[26rem] w-72 shrink-0" />)}</div></div>;
}
