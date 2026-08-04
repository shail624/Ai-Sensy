import {
  AlertTriangle,
  CheckCircle2,
  CheckSquare2,
  Columns3,
  FileCheck2,
  Filter,
  GripVertical,
  List,
  RefreshCw,
  Search,
  Tag,
  Users,
  X,
} from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  Input,
  Modal,
  Pagination,
  Select,
  Skeleton,
  Textarea,
  Toolbar,
  ToolbarDivider,
  ToolbarGroup,
} from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import {
  apiErrorMessage,
  useBulkUpdateReactivation,
  useReactivationPipeline,
  useTransitionReactivation,
} from "@/features/reactivation/api";
import {
  compareByUrgency,
  matchesOperationalView,
  REACTIVATION_OPERATIONAL_VIEWS,
  releaseRiskLabel,
  toAttentionSignal,
  type ReactivationOperationalView,
} from "@/features/reactivation/missionControl";
import { ReactivationCaseDrawer } from "@/features/reactivation/ReactivationCaseDrawer";
import {
  REACTIVATION_STAGE_LABELS,
  REACTIVATION_STAGES,
  REACTIVATION_LABEL_NAMES,
  REACTIVATION_LABELS,
  stageIndex,
  type ReactivationCard,
  type ReactivationLabel,
  type ReactivationStage,
} from "@/features/reactivation/types";
import { useHasPermission } from "@/lib/auth";

export const REACTIVATION_STAGE_BLUEPRINT = REACTIVATION_STAGES.map(
  (stage) => REACTIVATION_STAGE_LABELS[stage],
);

const PAGE_SIZE = 25;
type ViewMode = "board" | "list";
type SortMode = "urgency" | "updated" | "release";

interface PendingMove {
  card: ReactivationCard;
  target: ReactivationStage;
}

function operationalViewFrom(value: string | null): ReactivationOperationalView {
  return REACTIVATION_OPERATIONAL_VIEWS.some((view) => view.value === value)
    ? value as ReactivationOperationalView
    : "attention";
}

function sortModeFrom(value: string | null): SortMode {
  return value === "updated" || value === "release" ? value : "urgency";
}

function pageFrom(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function ReactivationPipelineBoard(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dropStage, setDropStage] = useState<ReactivationStage | null>(null);
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null);
  const [reason, setReason] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [bulkOwner, setBulkOwner] = useState("");
  const [bulkLabelAction, setBulkLabelAction] = useState("");

  const query = searchParams.get("q") ?? "";
  const ownerId = searchParams.get("owner") ?? "";
  const statusFilter = searchParams.get("status") ?? "";
  const labelFilter = searchParams.get("label") ?? "";
  const reminderView = searchParams.get("reminder") ?? "";
  const reminderDate = searchParams.get("date") ?? "";
  const operationalView = operationalViewFrom(searchParams.get("view"));
  const view: ViewMode = searchParams.get("mode") === "board" ? "board" : "list";
  const sortMode = sortModeFrom(searchParams.get("sort"));
  const page = pageFrom(searchParams.get("page"));
  const selectedCaseId = searchParams.get("case");
  const deferredQuery = useDeferredValue(query.trim());

  const canWrite = useHasPermission("reactivation:write");
  const canTransition = useHasPermission("reactivation:transition");
  const canReadUsers = useHasPermission("users:read");
  const users = useUsers(canReadUsers);
  const transition = useTransitionReactivation();
  const bulkUpdate = useBulkUpdateReactivation();

  const stageFromView = operationalView === "kyc"
    ? "kyc_verification"
    : operationalView === "sim"
      ? "sim_required"
      : operationalView === "activation"
        ? "activation_pending"
        : undefined;
  const pipeline = useReactivationPipeline({
    q: deferredQuery || undefined,
    stage: statusFilter
      ? [statusFilter as ReactivationStage]
      : stageFromView
        ? [stageFromView]
        : undefined,
    label: labelFilter
      ? [labelFilter as ReactivationLabel]
      : operationalView === "priority"
        ? ["priority"]
        : undefined,
    owner_user_id: ownerId || undefined,
    reminder_view: reminderView
      ? reminderView as "upcoming" | "due_today" | "overdue"
      : operationalView === "due_today"
        ? "due_today"
        : undefined,
    reminder_date: reminderDate || undefined,
    limit: 200,
  });

  function updateUrl(
    updates: Record<string, string | null>,
    options: { resetPage?: boolean; replace?: boolean } = {},
  ): void {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (options.resetPage !== false) next.delete("page");
    setSearchParams(next, { replace: options.replace ?? true });
  }

  const loadedCards = useMemo(() => pipeline.data?.data ?? [], [pipeline.data?.data]);
  const filteredCards = useMemo(() => {
    const matching = loadedCards.filter((card) => matchesOperationalView(card, operationalView));
    return matching.sort((a, b) => {
      if (sortMode === "updated") {
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
      if (sortMode === "release") {
        const aRelease = a.release_at ? new Date(a.release_at).getTime() : Number.POSITIVE_INFINITY;
        const bRelease = b.release_at ? new Date(b.release_at).getTime() : Number.POSITIVE_INFINITY;
        return aRelease - bRelease || compareByUrgency(a, b);
      }
      return compareByUrgency(a, b);
    });
  }, [loadedCards, operationalView, sortMode]);
  const pageCount = Math.max(1, Math.ceil(filteredCards.length / PAGE_SIZE));
  const pageCards = useMemo(
    () => filteredCards.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filteredCards, page],
  );
  const selected = selectedCaseId
    ? loadedCards.find((card) => card.id === selectedCaseId) ?? null
    : null;
  const selectedCards = useMemo(
    () => loadedCards.filter((card) => selectedIds.has(card.id)),
    [loadedCards, selectedIds],
  );

  useEffect(() => {
    if (page <= pageCount) return;
    const next = new URLSearchParams(searchParams);
    if (pageCount > 1) next.set("page", String(pageCount));
    else next.delete("page");
    setSearchParams(next, { replace: true });
  }, [page, pageCount, searchParams, setSearchParams]);

  useEffect(() => {
    const available = new Set(loadedCards.map((card) => card.id));
    setSelectedIds((current) => {
      const next = new Set(Array.from(current).filter((id) => available.has(id)));
      if (next.size === current.size) return current;
      return next;
    });
  }, [loadedCards]);

  const counts = useMemo(
    () => new Map((pipeline.data?.stage_counts ?? []).map((entry) => [entry.stage, entry.count])),
    [pipeline.data?.stage_counts],
  );
  const byStage = useMemo(() => {
    const result = new Map<ReactivationStage, ReactivationCard[]>();
    for (const stage of REACTIVATION_STAGES) result.set(stage, []);
    for (const card of pageCards) result.get(card.stage)?.push(card);
    return result;
  }, [pageCards]);

  const activeTotal = REACTIVATION_STAGES.filter(
    (stage) => !["completed", "not_required"].includes(stage),
  ).reduce((sum, stage) => sum + (counts.get(stage) ?? 0), 0);
  const completed = counts.get("completed") ?? 0;
  const attentionCount = loadedCards.filter((card) => matchesOperationalView(card, "attention")).length;
  const overdueCount = loadedCards.filter((card) => matchesOperationalView(card, "overdue")).length;
  const documentGapCount = loadedCards.filter((card) => matchesOperationalView(card, "documents")).length;
  const reminderCounts = pipeline.data?.reminder_counts ?? { upcoming: 0, due_today: 0, overdue: 0 };
  const activeFilterCount = [query, ownerId, statusFilter, labelFilter, reminderView, reminderDate]
    .filter(Boolean).length;
  const pageStart = filteredCards.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const pageEnd = Math.min(page * PAGE_SIZE, filteredCards.length);
  const allPageSelected = pageCards.length > 0 && pageCards.every((card) => selectedIds.has(card.id));

  function requestMove(card: ReactivationCard, target: ReactivationStage): void {
    if (!canTransition || !card.available_transitions.includes(target)) return;
    setPendingMove({ card, target });
    setReason("");
  }

  function confirmMove(): void {
    if (!pendingMove) return;
    const reasonRequired = pendingMove.target === "not_required";
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
    const card = loadedCards.find((candidate) => candidate.id === draggingId);
    setDraggingId(null);
    setDropStage(null);
    if (card) requestMove(card, target);
  }

  function toggleSelected(cardId: string, selectedValue: boolean): void {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (selectedValue) next.add(cardId);
      else next.delete(cardId);
      return next;
    });
  }

  function togglePageSelection(): void {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (allPageSelected) pageCards.forEach((card) => next.delete(card.id));
      else pageCards.forEach((card) => next.add(card.id));
      return next;
    });
  }

  function applyBulkUpdate(): void {
    if (!canWrite || selectedCards.length === 0) return;
    const ownerUserId = bulkOwner === "__unassigned"
      ? null
      : bulkOwner || undefined;
    const [labelOperation, labelValue] = bulkLabelAction.split(":") as [string, ReactivationLabel | undefined];
    bulkUpdate.mutate(
      {
        cards: selectedCards,
        ownerUserId,
        addLabel: labelOperation === "add" ? labelValue : undefined,
        removeLabel: labelOperation === "remove" ? labelValue : undefined,
      },
      {
        onSuccess: (result) => {
          if (result.failed === 0) setSelectedIds(new Set());
        },
      },
    );
  }

  function clearFilters(): void {
    const next = new URLSearchParams();
    next.set("view", operationalView);
    if (view === "board") next.set("mode", "board");
    if (sortMode !== "urgency") next.set("sort", sortMode);
    if (selectedCaseId) next.set("case", selectedCaseId);
    setSearchParams(next, { replace: true });
  }

  if (pipeline.isLoading) return <PipelineLoading />;
  if (pipeline.isError) {
    return <ErrorState message={apiErrorMessage(pipeline.error)} onRetry={() => void pipeline.refetch()} />;
  }

  return (
    <div className="space-y-4">
      <section aria-label="Pipeline summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Users} label="Active pipeline" value={activeTotal} detail={`${pipeline.data?.total ?? 0} source cases`} />
        <Metric icon={AlertTriangle} label="Attention now" value={attentionCount} detail="Ranked operational exceptions in the loaded set" tone={attentionCount > 0 ? "danger" : "neutral"} />
        <Metric icon={FileCheck2} label="Document gaps" value={documentGapCount} detail={`${reminderCounts.due_today} reminders due today`} tone={documentGapCount > 0 ? "warning" : "neutral"} />
        <Metric icon={CheckCircle2} label="Completed" value={completed} detail={`${overdueCount} loaded cases overdue or breached`} tone="success" />
      </section>

      <Card className="overflow-hidden" padding={false}>
        <div className="border-b border-border px-3 py-3 sm:px-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">Operational views</h2>
              <p className="mt-0.5 text-xs text-text-secondary">Bookmarkable URL views over the bounded tenant-scoped source set.</p>
            </div>
            <Badge tone="neutral">{filteredCards.length} matching loaded</Badge>
          </div>
          <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Reactivation operational views">
            {REACTIVATION_OPERATIONAL_VIEWS.map((item) => {
              const count = loadedCards.filter((card) => matchesOperationalView(card, item.value)).length;
              return (
                <button
                  key={item.value}
                  type="button"
                  role="tab"
                  aria-selected={operationalView === item.value}
                  title={item.description}
                  onClick={() => updateUrl({ view: item.value })}
                  className={`flex min-h-10 shrink-0 items-center gap-2 rounded-control border px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                    operationalView === item.value
                      ? "border-accent bg-accent text-accent-fg"
                      : "border-border bg-surface text-text-secondary hover:bg-hover hover:text-text-primary"
                  }`}
                >
                  {item.label}<span className={`rounded-full px-1.5 py-0.5 text-[10px] ${operationalView === item.value ? "bg-white/20" : "bg-surface-2"}`}>{count}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="p-3 sm:p-4">
          <FilterBar label="Reactivation case filters" className="border-0 p-0 shadow-none" contentClassName="items-end">
            <Field htmlFor="reactivation-search" label="Search cases" className="w-full md:min-w-72 md:flex-1">
              <Input
                id="reactivation-search"
                value={query}
                onChange={(event) => updateUrl({ q: event.target.value })}
                placeholder="Name, mobile or Vi number"
                leadingIcon={<Search aria-hidden className="h-4 w-4" />}
              />
            </Field>
            <Field htmlFor="reactivation-owner" label="Owner" className="w-full sm:w-48">
              <Select id="reactivation-owner" value={ownerId} onChange={(event) => updateUrl({ owner: event.target.value })} disabled={!canReadUsers}>
                <option value="">All owners</option>
                {(users.data?.data ?? []).filter((user) => user.is_active).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}
              </Select>
            </Field>
            <Field htmlFor="reactivation-status" label="Status" className="w-full sm:w-48">
              <Select id="reactivation-status" value={statusFilter} onChange={(event) => updateUrl({ status: event.target.value })}>
                <option value="">All statuses</option>
                {REACTIVATION_STAGES.map((stage) => <option key={stage} value={stage}>{REACTIVATION_STAGE_LABELS[stage]}</option>)}
              </Select>
            </Field>
            <Field htmlFor="reactivation-label" label="Label" className="w-full sm:w-48">
              <Select id="reactivation-label" value={labelFilter} onChange={(event) => updateUrl({ label: event.target.value })}>
                <option value="">All labels</option>
                {REACTIVATION_LABELS.map((label) => <option key={label} value={label}>{REACTIVATION_LABEL_NAMES[label]}</option>)}
              </Select>
            </Field>
            <Field htmlFor="reactivation-reminder" label="Reminder" className="w-full sm:w-40">
              <Select id="reactivation-reminder" value={reminderView} onChange={(event) => updateUrl({ reminder: event.target.value })}>
                <option value="">Any</option>
                <option value="due_today">Today</option>
                <option value="overdue">Overdue</option>
                <option value="upcoming">Upcoming</option>
              </Select>
            </Field>
            <Field htmlFor="reactivation-date" label="Reminder date" className="w-full sm:w-44">
              <Input id="reactivation-date" type="date" value={reminderDate} onChange={(event) => updateUrl({ date: event.target.value })} />
            </Field>
          </FilterBar>

          <Toolbar label="Pipeline display and filter actions" className="mt-3 border-t border-border pt-3">
            <ToolbarGroup grow>
              <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary"><Filter aria-hidden className="h-3.5 w-3.5" />{activeFilterCount} active filters</span>
              {activeFilterCount > 0 ? <Button variant="ghost" size="sm" leftIcon={<X aria-hidden className="h-3.5 w-3.5" />} onClick={clearFilters}>Clear filters</Button> : null}
            </ToolbarGroup>
            <ToolbarGroup>
              <label className="flex items-center gap-2 text-xs font-semibold text-text-secondary">
                Sort
                <Select aria-label="Sort Reactivation cases" controlSize="sm" value={sortMode} onChange={(event) => updateUrl({ sort: event.target.value === "urgency" ? null : event.target.value })} className="w-36">
                  <option value="urgency">Urgency</option>
                  <option value="updated">Recently updated</option>
                  <option value="release">Release date</option>
                </Select>
              </label>
              <ToolbarDivider />
              <div className="grid grid-cols-2 rounded-control border border-border bg-surface-2 p-1" aria-label="Pipeline view">
                <button type="button" aria-label="Kanban view" aria-pressed={view === "board"} onClick={() => updateUrl({ mode: "board" }, { resetPage: false })} className={`flex min-h-8 items-center gap-2 rounded-control px-3 text-xs font-semibold ${view === "board" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"}`}><Columns3 aria-hidden className="h-4 w-4" />Board</button>
                <button type="button" aria-label="List view" aria-pressed={view === "list"} onClick={() => updateUrl({ mode: null }, { resetPage: false })} className={`flex min-h-8 items-center gap-2 rounded-control px-3 text-xs font-semibold ${view === "list" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"}`}><List aria-hidden className="h-4 w-4" />List</button>
              </div>
              <Button variant="secondary" size="sm" leftIcon={<RefreshCw className={`h-4 w-4 ${pipeline.isFetching ? "animate-spin" : ""}`} />} onClick={() => void pipeline.refetch()}>Refresh</Button>
            </ToolbarGroup>
          </Toolbar>
        </div>
      </Card>

      {canWrite && selectedCards.length > 0 ? (
        <Card className="p-3" padding={false}>
          <Toolbar label="Bulk Reactivation actions" className="items-end">
            <ToolbarGroup grow>
              <span className="inline-flex min-h-9 items-center gap-2 text-sm font-semibold text-text-primary"><CheckSquare2 aria-hidden className="h-4 w-4 text-accent" />{selectedCards.length} selected</span>
              <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>Clear selection</Button>
            </ToolbarGroup>
            <Field htmlFor="bulk-owner" label="Assign owner" className="w-full sm:w-48">
              <Select id="bulk-owner" controlSize="sm" value={bulkOwner} onChange={(event) => setBulkOwner(event.target.value)} disabled={!canReadUsers}>
                <option value="">Leave unchanged</option>
                <option value="__unassigned">Set unassigned</option>
                {(users.data?.data ?? []).filter((user) => user.is_active).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}
              </Select>
            </Field>
            <Field htmlFor="bulk-label" label="Label action" className="w-full sm:w-52">
              <Select id="bulk-label" controlSize="sm" value={bulkLabelAction} onChange={(event) => setBulkLabelAction(event.target.value)}>
                <option value="">Leave unchanged</option>
                {REACTIVATION_LABELS.map((label) => <option key={`add-${label}`} value={`add:${label}`}>Add {REACTIVATION_LABEL_NAMES[label]}</option>)}
                {REACTIVATION_LABELS.map((label) => <option key={`remove-${label}`} value={`remove:${label}`}>Remove {REACTIVATION_LABEL_NAMES[label]}</option>)}
              </Select>
            </Field>
            <Button size="sm" loading={bulkUpdate.isPending} disabled={!bulkOwner && !bulkLabelAction} onClick={applyBulkUpdate}>Apply to selected</Button>
          </Toolbar>
          {bulkUpdate.data ? (
            <p role="status" className={`mt-2 text-xs ${bulkUpdate.data.failed > 0 ? "text-warning" : "text-success"}`}>
              {bulkUpdate.data.updated} updated{bulkUpdate.data.failed > 0 ? ` · ${bulkUpdate.data.failed} failed authorization or concurrency checks` : ""}.
            </p>
          ) : null}
        </Card>
      ) : null}

      {selectedCaseId && !selected ? (
        <Card className="flex flex-col gap-3 border-warning/50 bg-warning/10 p-4 sm:flex-row sm:items-center sm:justify-between" padding={false}>
          <div><p className="text-sm font-semibold text-text-primary">Linked case is not in the loaded source set</p><p className="mt-1 text-xs text-text-secondary">It may be outside the current bounded query or inaccessible to this role. No case metadata is disclosed.</p></div>
          <Button variant="secondary" size="sm" onClick={() => updateUrl({ case: null }, { resetPage: false })}>Dismiss link</Button>
        </Card>
      ) : null}

      {filteredCards.length === 0 ? (
        <Card><EmptyState icon={<Columns3 className="h-7 w-7" />} title={activeFilterCount > 0 || operationalView !== "all" ? "No cases match this operating view" : "No reactivation cases yet"} description={activeFilterCount > 0 || operationalView !== "all" ? "Choose another operational view or clear the explicit filters." : "Create a governed reactivation case from an existing contact to begin the pipeline."} action={activeFilterCount > 0 || operationalView !== "all" ? <Button variant="secondary" onClick={() => { const next = new URLSearchParams(); next.set("view", "all"); setSearchParams(next, { replace: true }); }}>Show all loaded cases</Button> : undefined} /></Card>
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
              canSelect={canWrite}
              selectedIds={selectedIds}
              onSelect={toggleSelected}
              onDragStart={setDraggingId}
              onDragEnd={() => { setDraggingId(null); setDropStage(null); }}
              onDragOver={() => setDropStage(stage)}
              onDrop={() => handleDrop(stage)}
              onOpen={(card) => updateUrl({ case: card.id }, { resetPage: false })}
              onMove={requestMove}
            />
          ))}
        </div>
      ) : (
        <PipelineList
          cards={pageCards}
          canSelect={canWrite}
          selectedIds={selectedIds}
          allPageSelected={allPageSelected}
          onTogglePage={togglePageSelection}
          onSelect={toggleSelected}
          onOpen={(card) => updateUrl({ case: card.id }, { resetPage: false })}
          onMove={requestMove}
          canTransition={canTransition}
        />
      )}

      <Pagination
        hasPrevious={page > 1}
        hasNext={page < pageCount}
        onPrevious={() => updateUrl({ page: page > 2 ? String(page - 1) : null }, { resetPage: false })}
        onNext={() => updateUrl({ page: String(page + 1) }, { resetPage: false })}
        busy={pipeline.isFetching}
        summary={<span>{pageStart}–{pageEnd} of {filteredCards.length} matching loaded records · {pipeline.data?.total ?? loadedCards.length} total source records</span>}
      />

      <p className="text-center text-[11px] leading-relaxed text-text-disabled">
        Pipeline reads are bounded to 200 source records. Operational views and pages are URL-persisted over that loaded set; source queues remain authoritative for complete enterprise pagination.
      </p>

      {selected ? <ReactivationCaseDrawer card={selected} onClose={() => updateUrl({ case: null }, { resetPage: false })} onMove={requestMove} /> : null}

      {pendingMove ? (
        <Modal title={`Move to ${REACTIVATION_STAGE_LABELS[pendingMove.target]}`} onClose={() => setPendingMove(null)}>
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">Move <strong className="text-text-primary">{pendingMove.card.contact_name}</strong> from {REACTIVATION_STAGE_LABELS[pendingMove.card.stage]}? This writes immutable stage, audit and Customer Timeline evidence.</p>
            <Field htmlFor="transition-reason" label={`Reason${pendingMove.target === "not_required" ? " (required)" : " (optional)"}`}>
              <Textarea id="transition-reason" value={reason} onChange={(event) => setReason(event.target.value)} rows={3} maxLength={2000} invalid={pendingMove.target === "not_required" && !reason.trim()} />
            </Field>
            {transition.error ? <ErrorState message={apiErrorMessage(transition.error)} /> : null}
            <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setPendingMove(null)}>Cancel</Button><Button disabled={transition.isPending || (pendingMove.target === "not_required" && !reason.trim())} onClick={confirmMove}>{transition.isPending ? "Moving…" : "Confirm move"}</Button></div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

function PipelineColumn({
  stage,
  cards,
  total,
  draggingId,
  activeDrop,
  canTransition,
  canSelect,
  selectedIds,
  onSelect,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onOpen,
  onMove,
}: {
  stage: ReactivationStage;
  cards: ReactivationCard[];
  total: number;
  draggingId: string | null;
  activeDrop: boolean;
  canTransition: boolean;
  canSelect: boolean;
  selectedIds: Set<string>;
  onSelect: (id: string, selected: boolean) => void;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOver: () => void;
  onDrop: () => void;
  onOpen: (card: ReactivationCard) => void;
  onMove: (card: ReactivationCard, target: ReactivationStage) => void;
}): JSX.Element {
  const dragged = cards.find((card) => card.id === draggingId);
  return (
    <section
      className={`min-h-[26rem] w-[19rem] shrink-0 snap-start rounded-surface border bg-surface-2 p-3 transition ${activeDrop && !dragged ? "border-accent ring-2 ring-focus/20" : "border-border"}`}
      aria-label={REACTIVATION_STAGE_LABELS[stage]}
      onDragOver={(event) => { event.preventDefault(); onDragOver(); }}
      onDrop={(event) => { event.preventDefault(); onDrop(); }}
    >
      <header className="mb-3 flex items-center justify-between gap-2"><div><h2 className="text-sm font-semibold text-text-primary">{REACTIVATION_STAGE_LABELS[stage]}</h2><p className="mt-0.5 text-[11px] text-text-disabled">{cards.length} on this page</p></div><Badge tone={stage === "completed" ? "success" : stage === "not_required" ? "danger" : "neutral"}>{total}</Badge></header>
      <div className="space-y-2">
        {cards.map((card) => <PipelineCard key={card.id} card={card} canTransition={canTransition} canSelect={canSelect} selected={selectedIds.has(card.id)} dragging={draggingId === card.id} onSelect={(value) => onSelect(card.id, value)} onDragStart={() => onDragStart(card.id)} onDragEnd={onDragEnd} onOpen={() => onOpen(card)} onMove={(target) => onMove(card, target)} />)}
        {cards.length === 0 ? <EmptyState compact title="No cases on this page" description="Choose another view or page. The server validates every permitted move." /> : null}
      </div>
    </section>
  );
}

function PipelineCard({
  card,
  canTransition,
  canSelect,
  selected,
  dragging,
  onSelect,
  onDragStart,
  onDragEnd,
  onOpen,
  onMove,
}: {
  card: ReactivationCard;
  canTransition: boolean;
  canSelect: boolean;
  selected: boolean;
  dragging: boolean;
  onSelect: (selected: boolean) => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onOpen: () => void;
  onMove: (target: ReactivationStage) => void;
}): JSX.Element {
  const signal = toAttentionSignal(card);
  const releaseRisk = releaseRiskLabel(card);
  function keyboardMove(direction: -1 | 1): void {
    const current = stageIndex(card.stage);
    const ordered = card.available_transitions.slice().sort((a, b) => stageIndex(a) - stageIndex(b));
    const target = direction > 0
      ? ordered.find((stage) => stageIndex(stage) > current)
      : ordered.slice().reverse().find((stage) => stageIndex(stage) < current);
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
      className={`group rounded-control border bg-surface p-3 shadow-sm outline-none transition hover:border-accent focus-visible:ring-2 focus-visible:ring-focus ${selected ? "border-accent ring-1 ring-accent/30" : "border-border"} ${canTransition ? "cursor-grab" : ""} ${dragging ? "opacity-50" : ""}`}
      aria-label={`${card.contact_name}, ${REACTIVATION_STAGE_LABELS[card.stage]}`}
    >
      <div className="flex items-start gap-2">
        {canSelect ? <input aria-label={`Select ${card.contact_name}`} type="checkbox" checked={selected} onChange={(event) => onSelect(event.target.checked)} className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-focus" /> : <GripVertical aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-text-disabled" />}
        <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"><span className="block truncate text-sm font-semibold text-text-primary group-hover:text-accent">{card.contact_name}</span><span className="mt-0.5 block text-xs text-text-secondary">{card.contact_phone}</span></button>
        <Badge tone={signal.severity === "critical" ? "danger" : signal.severity === "high" ? "warning" : signal.severity === "medium" ? "info" : "neutral"}>{signal.severity}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {signal.reasons.slice(0, 2).map((item) => <Badge key={item} tone={item.includes("SLA") || item.includes("overdue") ? "danger" : "neutral"}>{item}</Badge>)}
        {card.labels.map((label) => <Badge key={label} tone={label === "priority" ? "danger" : label === "follow_up" ? "info" : "neutral"}><Tag aria-hidden className="mr-1 h-3 w-3" />{REACTIVATION_LABEL_NAMES[label]}</Badge>)}
      </div>
      <p className="mt-3 border-t border-border pt-2 text-[11px] font-medium leading-relaxed text-text-primary">{signal.nextAction}</p>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-[11px]"><div><dt className="text-text-disabled">Owner</dt><dd className="truncate font-medium text-text-secondary">{card.owner_name ?? "Unassigned"}</dd></div><div><dt className="text-text-disabled">Documents</dt><dd className="font-medium text-text-secondary">{card.verified_document_count}/{card.document_count}</dd></div>{releaseRisk ? <div className="col-span-2"><dt className="text-text-disabled">Release</dt><dd className="font-medium text-warning">{releaseRisk}</dd></div> : null}</dl>
    </article>
  );
}

function PipelineList({
  cards,
  canSelect,
  selectedIds,
  allPageSelected,
  onTogglePage,
  onSelect,
  onOpen,
  onMove,
  canTransition,
}: {
  cards: ReactivationCard[];
  canSelect: boolean;
  selectedIds: Set<string>;
  allPageSelected: boolean;
  onTogglePage: () => void;
  onSelect: (id: string, selected: boolean) => void;
  onOpen: (card: ReactivationCard) => void;
  onMove: (card: ReactivationCard, stage: ReactivationStage) => void;
  canTransition: boolean;
}): JSX.Element {
  return (
    <Card className="overflow-hidden" padding={false}>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase tracking-wide text-text-secondary">
            <tr>
              {canSelect ? <th className="w-12 px-4 py-3"><input aria-label="Select all cases on this page" type="checkbox" checked={allPageSelected} onChange={onTogglePage} className="h-4 w-4 rounded border-border text-accent focus:ring-focus" /></th> : null}
              <th className="px-4 py-3">Customer</th><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Next action</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Owner</th><th className="px-4 py-3">Evidence</th><th className="px-4 py-3">Move</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {cards.map((card) => {
              const signal = toAttentionSignal(card);
              return <tr key={card.id} className={selectedIds.has(card.id) ? "bg-accent-soft/50" : "hover:bg-hover"}>
                {canSelect ? <td className="px-4 py-3"><input aria-label={`Select ${card.contact_name}`} type="checkbox" checked={selectedIds.has(card.id)} onChange={(event) => onSelect(card.id, event.target.checked)} className="h-4 w-4 rounded border-border text-accent focus:ring-focus" /></td> : null}
                <td className="px-4 py-3"><button type="button" onClick={() => onOpen(card)} className="font-semibold text-text-primary hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">{card.contact_name}</button><p className="mt-0.5 text-xs text-text-secondary">{card.contact_phone}</p></td>
                <td className="px-4 py-3"><div className="flex max-w-56 flex-wrap gap-1"><Badge tone={signal.severity === "critical" ? "danger" : signal.severity === "high" ? "warning" : signal.severity === "medium" ? "info" : "neutral"}>{signal.severity}</Badge>{signal.reasons.slice(0, 2).map((item) => <Badge key={item} tone="neutral">{item}</Badge>)}</div></td>
                <td className="max-w-xs px-4 py-3 text-xs leading-relaxed text-text-primary">{signal.nextAction}</td>
                <td className="px-4 py-3"><Badge>{REACTIVATION_STAGE_LABELS[card.stage]}</Badge></td>
                <td className="px-4 py-3 text-text-secondary">{card.owner_name ?? "Unassigned"}</td>
                <td className="px-4 py-3 text-xs text-text-secondary">{card.verified_document_count}/{card.document_count} verified{card.release_at ? <span className="mt-1 block">Release {new Date(card.release_at).toLocaleDateString()}</span> : null}</td>
                <td className="px-4 py-3"><Select aria-label={`Move ${card.contact_name}`} controlSize="sm" disabled={!canTransition || card.available_transitions.length === 0} defaultValue="" onChange={(event) => { if (event.target.value) onMove(card, event.target.value as ReactivationStage); event.target.value = ""; }} className="w-40"><option value="">Move…</option>{card.available_transitions.map((target) => <option key={target} value={target}>{REACTIVATION_STAGE_LABELS[target]}</option>)}</Select></td>
              </tr>;
            })}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-border md:hidden">
        {canSelect ? <label className="flex min-h-11 items-center gap-2 bg-surface-2 px-4 text-xs font-semibold text-text-secondary"><input type="checkbox" checked={allPageSelected} onChange={onTogglePage} className="h-4 w-4 rounded border-border text-accent focus:ring-focus" />Select this page</label> : null}
        {cards.map((card) => {
          const signal = toAttentionSignal(card);
          return <article key={card.id} className={`p-4 ${selectedIds.has(card.id) ? "bg-accent-soft/50" : ""}`}>
            <div className="flex items-start gap-3">
              {canSelect ? <input aria-label={`Select ${card.contact_name}`} type="checkbox" checked={selectedIds.has(card.id)} onChange={(event) => onSelect(card.id, event.target.checked)} className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-focus" /> : null}
              <button type="button" onClick={() => onOpen(card)} className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"><span className="flex items-start justify-between gap-3"><span><span className="block truncate text-sm font-semibold text-text-primary">{card.contact_name}</span><span className="mt-1 block text-xs text-text-secondary">{REACTIVATION_STAGE_LABELS[card.stage]} · {card.owner_name ?? "Unassigned"}</span></span><Badge tone={signal.severity === "critical" ? "danger" : signal.severity === "high" ? "warning" : "info"}>{signal.severity}</Badge></span><span className="mt-3 block text-xs font-medium leading-relaxed text-text-primary">{signal.nextAction}</span><span className="mt-2 flex flex-wrap gap-1">{signal.reasons.slice(0, 2).map((item) => <Badge key={item} tone="neutral">{item}</Badge>)}</span></button>
            </div>
          </article>;
        })}
      </div>
    </Card>
  );
}

function Metric({ icon: Icon, label, value, detail, tone = "neutral" }: { icon: typeof Users; label: string; value: number; detail: string; tone?: "neutral" | "success" | "warning" | "danger" }): JSX.Element {
  const toneClass = tone === "success" ? "bg-success/10 text-success" : tone === "warning" ? "bg-warning/10 text-warning" : tone === "danger" ? "bg-danger/10 text-danger" : "bg-accent-soft text-accent";
  return <Card className="flex items-center gap-3 p-4" padding={false}><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-control ${toneClass}`}><Icon aria-hidden className="h-5 w-5" /></span><div className="min-w-0"><p className="text-xl font-bold text-text-primary">{value}</p><p className="text-xs font-semibold text-text-secondary">{label}</p><p className="mt-0.5 truncate text-[11px] text-text-disabled">{detail}</p></div></Card>;
}

function PipelineLoading(): JSX.Element {
  return <div aria-label="Loading reactivation pipeline" className="space-y-4"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-24 w-full" />)}</div><Skeleton className="h-40 w-full" /><div className="flex gap-3 overflow-hidden">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-[26rem] w-72 shrink-0" />)}</div></div>;
}
