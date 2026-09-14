import {
  AlertTriangle,
  Bookmark,
  CalendarClock,
  CheckCircle2,
  Columns3,
  Filter,
  GripVertical,
  List,
  Lock,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Tag,
  Trash2,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
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
  Toolbar,
  ToolbarGroup,
} from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import {
  apiErrorMessage,
  useCreateReactivationView,
  useDeleteReactivationView,
  useReactivationPipeline,
  useReactivationViews,
  useTransitionReactivation,
} from "@/features/reactivation/api";
import { ReactivationCaseDrawer } from "@/features/reactivation/ReactivationCaseDrawer";
import {
  REACTIVATION_LABEL_NAMES,
  REACTIVATION_LABELS,
  REACTIVATION_STAGE_LABELS,
  REACTIVATION_STAGES,
  stageIndex,
  type ReactivationCard,
  type ReactivationLabel,
  type ReactivationStage,
  type ReactivationView,
  type ReactivationViewCreate,
} from "@/features/reactivation/types";
import { useHasPermission } from "@/lib/auth";

export const REACTIVATION_STAGE_BLUEPRINT = REACTIVATION_STAGES.map(
  (stage) => REACTIVATION_STAGE_LABELS[stage],
);

const PAGE_SIZE = 25;

type ViewMode = "board" | "list";
type ReminderView = "upcoming" | "due_today" | "overdue";
type WorkView = "all" | "due_today" | "overdue" | "completed";

interface PendingMove {
  card: ReactivationCard;
  target: ReactivationStage;
}

function positivePage(value: string | null): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export function ReactivationPipelineBoard(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dropStage, setDropStage] = useState<ReactivationStage | null>(null);
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null);
  const [reason, setReason] = useState("");
  const [viewsOpen, setViewsOpen] = useState(false);

  const query = searchParams.get("q") ?? "";
  const ownerId = searchParams.get("owner") ?? "";
  const statusFilter = searchParams.get("stage") ?? "";
  const labelFilter = searchParams.get("label") ?? "";
  const reminderView = searchParams.get("reminder") ?? "";
  const reminderDate = searchParams.get("date") ?? "";
  const view: ViewMode = searchParams.get("view") === "list" ? "list" : "board";
  const page = positivePage(searchParams.get("page"));
  const deferredQuery = useDeferredValue(query.trim());

  const canTransition = useHasPermission("reactivation:transition");
  const canManageSharedViews = useHasPermission("reactivation:views_manage");
  const canReadUsers = useHasPermission("users:read");
  const users = useUsers(canReadUsers);
  const savedViews = useReactivationViews();
  const pipeline = useReactivationPipeline({
    q: deferredQuery || undefined,
    stage: statusFilter ? [statusFilter as ReactivationStage] : undefined,
    label: labelFilter ? [labelFilter as ReactivationLabel] : undefined,
    owner_user_id: ownerId || undefined,
    reminder_view: reminderView ? (reminderView as ReminderView) : undefined,
    reminder_date: reminderDate || undefined,
    offset: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
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
    (stage) => !["completed", "not_required"].includes(stage),
  ).reduce((sum, stage) => sum + (counts.get(stage) ?? 0), 0);
  const completed = counts.get("completed") ?? 0;
  const closed = completed + (counts.get("not_required") ?? 0);
  const conversionRate = closed > 0 ? Math.round((completed / closed) * 100) : 0;
  const reminderCounts = pipeline.data?.reminder_counts ?? {
    upcoming: 0,
    due_today: 0,
    overdue: 0,
  };
  const total = pipeline.data?.total ?? 0;
  const offset = (page - 1) * PAGE_SIZE;
  const firstVisible = cards.length > 0 ? offset + 1 : 0;
  const lastVisible = offset + cards.length;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = Boolean(
    query || ownerId || statusFilter || labelFilter || reminderView || reminderDate,
  );
  const workView: WorkView =
    statusFilter === "completed"
      ? "completed"
      : reminderView === "due_today"
        ? "due_today"
        : reminderView === "overdue"
          ? "overdue"
          : "all";

  function replaceParams(updates: Record<string, string | null>, resetPage = true): void {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetPage) next.delete("page");
    setSearchParams(next, { replace: true });
  }

  function selectWorkView(nextView: WorkView): void {
    replaceParams({
      reminder: nextView === "due_today" || nextView === "overdue" ? nextView : null,
      stage: nextView === "completed" ? "completed" : null,
      date: null,
    });
  }

  function currentViewFilters(): ReactivationViewCreate["filters"] {
    return {
      q: query.trim() || undefined,
      stage: statusFilter ? (statusFilter as ReactivationStage) : undefined,
      label: labelFilter ? (labelFilter as ReactivationLabel) : undefined,
      owner_user_id: ownerId || undefined,
      reminder_view: reminderView ? (reminderView as ReminderView) : undefined,
      reminder_date: reminderDate || undefined,
    };
  }

  function applySavedView(saved: ReactivationView): void {
    const next = new URLSearchParams();
    const filters = saved.filters;
    if (filters.q) next.set("q", filters.q);
    if (filters.owner_user_id) next.set("owner", filters.owner_user_id);
    if (filters.stage) next.set("stage", filters.stage);
    if (filters.label) next.set("label", filters.label);
    if (filters.reminder_view) next.set("reminder", filters.reminder_view);
    if (filters.reminder_date) next.set("date", filters.reminder_date);
    if (saved.display === "list") next.set("view", "list");
    setSearchParams(next, { replace: true });
  }

  function clearFilters(): void {
    const next = new URLSearchParams();
    if (view === "list") next.set("view", "list");
    setSearchParams(next, { replace: true });
  }

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
    const card = cards.find((candidate) => candidate.id === draggingId);
    setDraggingId(null);
    setDropStage(null);
    if (card) requestMove(card, target);
  }

  if (pipeline.isLoading) return <PipelineLoading />;
  if (pipeline.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(pipeline.error)}
        onRetry={() => void pipeline.refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <section aria-label="Pipeline summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          icon={Users}
          label="Active pipeline"
          value={activeTotal}
          detail={`${pipeline.data?.stage_counts.reduce((sum, item) => sum + item.count, 0) ?? 0} total cases`}
          active={workView === "all"}
          onClick={() => selectWorkView("all")}
        />
        <Metric
          icon={CalendarClock}
          label="Due today"
          value={reminderCounts.due_today}
          detail="Assigned reminders requiring action"
          tone={reminderCounts.due_today > 0 ? "warning" : "neutral"}
          active={workView === "due_today"}
          onClick={() => selectWorkView("due_today")}
        />
        <Metric
          icon={AlertTriangle}
          label="Overdue"
          value={reminderCounts.overdue}
          detail="Open until completed or rescheduled"
          tone={reminderCounts.overdue > 0 ? "danger" : "neutral"}
          active={workView === "overdue"}
          onClick={() => selectWorkView("overdue")}
        />
        <Metric
          icon={CheckCircle2}
          label="Completed"
          value={completed}
          detail={`${conversionRate}% closed-case conversion`}
          tone="success"
          active={workView === "completed"}
          onClick={() => selectWorkView("completed")}
        />
      </section>

      <FilterBar label="Reactivation pipeline filters" className="space-y-3">
        <div className="grid w-full gap-3 sm:grid-cols-2 xl:grid-cols-12 xl:items-end">
          <Field htmlFor="reactivation-search" label="Search cases" className="sm:col-span-2 xl:col-span-3">
            <Input
              id="reactivation-search"
              value={query}
              onChange={(event) => replaceParams({ q: event.target.value })}
              placeholder="Name, mobile or Vi number"
              leadingIcon={<Search aria-hidden className="h-4 w-4" />}
            />
          </Field>
          <Field htmlFor="reactivation-owner" label="Owner" className="xl:col-span-2">
            <Select
              id="reactivation-owner"
              value={ownerId}
              onChange={(event) => replaceParams({ owner: event.target.value })}
              disabled={!canReadUsers}
              title={!canReadUsers ? "Your role cannot list staff members." : undefined}
            >
              <option value="">All owners</option>
              {(users.data?.data ?? [])
                .filter((user) => user.is_active)
                .map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field htmlFor="reactivation-status" label="Status" className="xl:col-span-2">
            <Select
              id="reactivation-status"
              aria-label="Filter by status"
              value={statusFilter}
              onChange={(event) => replaceParams({ stage: event.target.value })}
            >
              <option value="">All statuses</option>
              {REACTIVATION_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {REACTIVATION_STAGE_LABELS[stage]}
                </option>
              ))}
            </Select>
          </Field>
          <Field htmlFor="reactivation-label" label="Label" className="xl:col-span-2">
            <Select
              id="reactivation-label"
              aria-label="Filter by label"
              value={labelFilter}
              onChange={(event) => replaceParams({ label: event.target.value })}
            >
              <option value="">All labels</option>
              {REACTIVATION_LABELS.map((label) => (
                <option key={label} value={label}>
                  {REACTIVATION_LABEL_NAMES[label]}
                </option>
              ))}
            </Select>
          </Field>
          <Field htmlFor="reactivation-reminder" label="Reminder" className="xl:col-span-1">
            <Select
              id="reactivation-reminder"
              aria-label="Filter by reminder view"
              value={reminderView}
              onChange={(event) => replaceParams({ reminder: event.target.value })}
            >
              <option value="">Any</option>
              <option value="due_today">Today</option>
              <option value="overdue">Overdue</option>
              <option value="upcoming">Upcoming</option>
            </Select>
          </Field>
          <Field htmlFor="reactivation-date" label="Reminder date" className="xl:col-span-2">
            <Input
              id="reactivation-date"
              aria-label="Filter by reminder date"
              type="date"
              value={reminderDate}
              onChange={(event) => replaceParams({ date: event.target.value })}
            />
          </Field>
        </div>

        <Toolbar
          label="Pipeline display controls"
          className="w-full border-t border-border pt-3"
        >
          <ToolbarGroup grow>
            <span className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
              <Filter aria-hidden className="h-3.5 w-3.5" />
              Work views
            </span>
            {(["all", "due_today", "overdue", "completed"] as const).map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={workView === item}
                onClick={() => selectWorkView(item)}
                className={`min-h-9 rounded-control px-3 text-xs font-semibold transition-colors ${
                  workView === item
                    ? "bg-accent text-accent-fg"
                    : "border border-border bg-surface text-text-secondary hover:bg-hover hover:text-text-primary"
                }`}
              >
                {item === "all"
                  ? "All active"
                  : item === "due_today"
                    ? "Due today"
                    : item === "overdue"
                      ? "Overdue"
                      : "Completed"}
              </button>
            ))}
            {hasFilters ? (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<X aria-hidden className="h-4 w-4" />}
                onClick={clearFilters}
              >
                Clear filters
              </Button>
            ) : null}
          </ToolbarGroup>
          <ToolbarGroup>
            <div
              className="grid grid-cols-2 rounded-control border border-border bg-surface-2 p-1"
              aria-label="Pipeline view"
            >
              <button
                type="button"
                aria-label="Kanban view"
                aria-pressed={view === "board"}
                onClick={() => replaceParams({ view: null }, false)}
                className={`flex min-h-9 items-center gap-2 rounded-control px-3 text-xs font-semibold ${
                  view === "board" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"
                }`}
              >
                <Columns3 aria-hidden className="h-4 w-4" />
                Board
              </button>
              <button
                type="button"
                aria-label="List view"
                aria-pressed={view === "list"}
                onClick={() => replaceParams({ view: "list" }, false)}
                className={`flex min-h-9 items-center gap-2 rounded-control px-3 text-xs font-semibold ${
                  view === "list" ? "bg-surface text-accent shadow-sm" : "text-text-secondary"
                }`}
              >
                <List aria-hidden className="h-4 w-4" />
                List
              </button>
            </div>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={
                <RefreshCw
                  aria-hidden
                  className={`h-4 w-4 ${pipeline.isFetching ? "animate-spin" : ""}`}
                />
              }
              onClick={() => void pipeline.refetch()}
            >
              Refresh
            </Button>
          </ToolbarGroup>
        </Toolbar>

        <div className="flex w-full flex-wrap items-center gap-2 border-t border-border pt-3">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
            <Bookmark aria-hidden className="h-3.5 w-3.5" />
            Saved views
          </span>
          {savedViews.isLoading ? (
            <span className="text-xs text-text-disabled">Loading…</span>
          ) : savedViews.isError ? (
            <span className="text-xs text-danger">Saved views unavailable</span>
          ) : (savedViews.data ?? []).length > 0 ? (
            <div
              aria-label="Personal and team Reactivation views"
              className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto"
            >
              {(savedViews.data ?? []).map((saved) => (
                <button
                  key={saved.id}
                  type="button"
                  onClick={() => applySavedView(saved)}
                  className="inline-flex min-h-8 shrink-0 items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 text-[11px] font-semibold text-text-primary hover:border-accent hover:text-accent"
                >
                  {saved.visibility === "private" ? (
                    <Lock aria-hidden className="h-3 w-3 text-text-disabled" />
                  ) : (
                    <Users aria-hidden className="h-3 w-3 text-accent" />
                  )}
                  {saved.name}
                </button>
              ))}
            </div>
          ) : (
            <span className="min-w-0 flex-1 text-xs text-text-disabled">
              Save the current filters for one-click reuse.
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Save aria-hidden className="h-4 w-4" />}
            onClick={() => setViewsOpen(true)}
          >
            Save / manage
          </Button>
        </div>

        <div className="flex w-full flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-text-secondary">
          <span aria-live="polite">
            {cards.length > 0
              ? `${firstVisible}–${lastVisible} of ${total} matching cases`
              : `0 of ${total} matching cases`}
            {" · "}
            {reminderCounts.upcoming} upcoming
          </span>
          <span className="text-text-disabled">
            Filters persist in this URL; saved views reopen without carrying page position.
          </span>
        </div>
      </FilterBar>

      {viewsOpen ? (
        <ReactivationViewsDialog
          filters={currentViewFilters()}
          display={view}
          views={savedViews.data ?? []}
          canManageShared={canManageSharedViews}
          onClose={() => setViewsOpen(false)}
        />
      ) : null}

      {cards.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Columns3 className="h-7 w-7" />}
            title={hasFilters ? "No cases match these filters" : "No reactivation cases yet"}
            description={
              hasFilters
                ? "Clear a filter, return to an earlier page, or search another customer."
                : "Create a governed reactivation case from an existing contact to begin the pipeline."
            }
            action={
              hasFilters ? (
                <Button variant="secondary" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : view === "board" ? (
        <div
          className="flex snap-x gap-3 overflow-x-auto pb-4"
          aria-label="Reactivation pipeline stages"
        >
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
              onDragEnd={() => {
                setDraggingId(null);
                setDropStage(null);
              }}
              onDragOver={() => setDropStage(stage)}
              onDrop={() => handleDrop(stage)}
              onOpen={(card) => setSelectedId(card.id)}
              onMove={requestMove}
            />
          ))}
        </div>
      ) : (
        <PipelineList
          cards={cards}
          onOpen={(card) => setSelectedId(card.id)}
          onMove={requestMove}
          canTransition={canTransition}
        />
      )}

      <Pagination
        label="Reactivation cases pagination"
        hasPrevious={page > 1}
        hasNext={offset + cards.length < total}
        busy={pipeline.isFetching}
        onPrevious={() => replaceParams({ page: String(Math.max(1, page - 1)) }, false)}
        onNext={() => replaceParams({ page: String(page + 1) }, false)}
        summary={
          <span>
            Page {page} of {pageCount}
          </span>
        }
      />

      {selected ? (
        <ReactivationCaseDrawer
          card={selected}
          onClose={() => setSelectedId(null)}
          onMove={requestMove}
        />
      ) : null}

      {pendingMove ? (
        <Modal
          title={`Move to ${REACTIVATION_STAGE_LABELS[pendingMove.target]}`}
          onClose={() => setPendingMove(null)}
        >
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">
              Move{" "}
              <strong className="text-text-primary">{pendingMove.card.contact_name}</strong> from{" "}
              {REACTIVATION_STAGE_LABELS[pendingMove.card.stage]}? This writes immutable stage,
              audit, and Customer Timeline evidence.
            </p>
            <label className="block text-xs font-semibold text-text-secondary">
              Reason
              {pendingMove.target === "not_required" ? " (required)" : " (optional)"}
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
                maxLength={2000}
                className="mt-1 w-full rounded-control border border-border bg-surface p-3 text-sm text-text-primary outline-none focus:border-accent focus-visible:ring-2 focus-visible:ring-focus"
              />
            </label>
            {transition.error ? <ErrorState message={apiErrorMessage(transition.error)} /> : null}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setPendingMove(null)}>
                Cancel
              </Button>
              <Button
                disabled={
                  transition.isPending ||
                  (pendingMove.target === "not_required" && !reason.trim())
                }
                onClick={confirmMove}
              >
                {transition.isPending ? "Moving…" : "Confirm move"}
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

interface ReactivationViewsDialogProps {
  filters: ReactivationViewCreate["filters"];
  display: ViewMode;
  views: ReactivationView[];
  canManageShared: boolean;
  onClose: () => void;
}

function ReactivationViewsDialog({
  filters,
  display,
  views,
  canManageShared,
  onClose,
}: ReactivationViewsDialogProps): JSX.Element {
  const [name, setName] = useState("");
  const [visibility, setVisibility] = useState<"private" | "shared">("private");
  const [pendingDelete, setPendingDelete] = useState<ReactivationView | null>(null);
  const createView = useCreateReactivationView();
  const deleteView = useDeleteReactivationView();

  function save(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!name.trim()) return;
    createView.mutate(
      { name, visibility, display, filters },
      { onSuccess: onClose },
    );
  }

  function confirmDelete(): void {
    if (!pendingDelete) return;
    deleteView.mutate(pendingDelete.id, {
      onSuccess: () => setPendingDelete(null),
    });
  }

  const privateViews = views.filter((saved) => saved.visibility === "private");
  const sharedViews = views.filter((saved) => saved.visibility === "shared");

  return (
    <Modal title="Reactivation saved views" variant="sheet" onClose={onClose}>
      <form className="space-y-4" onSubmit={save}>
        <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
          <Field htmlFor="reactivation-view-name" label="View name">
            <Input
              id="reactivation-view-name"
              autoFocus
              value={name}
              maxLength={80}
              onChange={(event) => setName(event.target.value)}
              placeholder="Example: Priority follow-ups"
            />
          </Field>
          <Field htmlFor="reactivation-view-visibility" label="Visible to">
            <Select
              id="reactivation-view-visibility"
              value={visibility}
              onChange={(event) =>
                setVisibility(event.target.value as "private" | "shared")
              }
            >
              <option value="private">Only me</option>
              <option value="shared" disabled={!canManageShared}>
                Whole team
              </option>
            </Select>
          </Field>
        </div>
        {!canManageShared ? (
          <p className="text-xs text-text-disabled">
            Your role can save personal views. A Reactivation manager can publish team views.
          </p>
        ) : null}
        {createView.error ? (
          <p role="alert" className="text-sm text-danger">
            {apiErrorMessage(createView.error)}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={createView.isPending}
            disabled={!name.trim() || (visibility === "shared" && !canManageShared)}
          >
            Save current view
          </Button>
        </div>
      </form>

      <div className="mt-5 space-y-4 border-t border-border pt-4">
        <SavedViewGroup
          title="Only me"
          icon={Lock}
          empty="No personal views yet."
          views={privateViews}
          onDelete={setPendingDelete}
        />
        <SavedViewGroup
          title="Whole team"
          icon={Users}
          empty="No team views yet."
          views={sharedViews}
          onDelete={setPendingDelete}
        />
      </div>

      {pendingDelete ? (
        <div className="mt-4 rounded-lg border border-danger/30 bg-danger/5 p-3">
          <p className="text-sm font-semibold text-text-primary">
            Delete “{pendingDelete.name}”?
          </p>
          <p className="mt-1 text-xs text-text-secondary">
            This removes the saved definition only. No Reactivation cases are changed.
          </p>
          {deleteView.error ? (
            <p role="alert" className="mt-2 text-sm text-danger">
              {apiErrorMessage(deleteView.error)}
            </p>
          ) : null}
          <div className="mt-3 flex justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPendingDelete(null)}
            >
              Keep view
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleteView.isPending}
              onClick={confirmDelete}
            >
              Delete view
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

interface SavedViewGroupProps {
  title: string;
  icon: LucideIcon;
  empty: string;
  views: ReactivationView[];
  onDelete: (view: ReactivationView) => void;
}

function SavedViewGroup({
  title,
  icon: Icon,
  empty,
  views,
  onDelete,
}: SavedViewGroupProps): JSX.Element {
  return (
    <section aria-label={`${title} saved views`}>
      <h3 className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
        <Icon aria-hidden className="h-3.5 w-3.5" />
        {title}
      </h3>
      {views.length === 0 ? (
        <p className="mt-2 text-xs text-text-disabled">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {views.map((saved) => (
            <li
              key={saved.id}
              className="flex items-center justify-between gap-3 rounded-control border border-border bg-surface-2 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{saved.name}</p>
                <p className="text-[11px] text-text-disabled">
                  Opens in {saved.display === "board" ? "board" : "list"} view
                </p>
              </div>
              {saved.can_delete ? (
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Delete ${saved.name}`}
                  leftIcon={<Trash2 aria-hidden className="h-4 w-4" />}
                  onClick={() => onDelete(saved)}
                >
                  Delete
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PipelineColumn({
  stage,
  cards,
  total,
  draggingId,
  activeDrop,
  canTransition,
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
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOver: () => void;
  onDrop: () => void;
  onOpen: (card: ReactivationCard) => void;
  onMove: (card: ReactivationCard, target: ReactivationStage) => void;
}): JSX.Element {
  return (
    <section
      className={`min-h-[26rem] w-[18rem] shrink-0 snap-start rounded-surface border bg-surface-2 p-3 transition ${
        activeDrop ? "border-accent ring-2 ring-focus/20" : "border-border"
      }`}
      aria-label={REACTIVATION_STAGE_LABELS[stage]}
      onDragOver={(event) => {
        event.preventDefault();
        onDragOver();
      }}
      onDrop={(event) => {
        event.preventDefault();
        onDrop();
      }}
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">
            {REACTIVATION_STAGE_LABELS[stage]}
          </h2>
          <p className="mt-0.5 text-[11px] text-text-disabled">
            {cards.length} on this page · {total} total
          </p>
        </div>
        <Badge
          tone={stage === "completed" ? "success" : stage === "not_required" ? "danger" : "neutral"}
        >
          {total}
        </Badge>
      </header>
      <div className="space-y-2">
        {cards.map((card) => (
          <PipelineCard
            key={card.id}
            card={card}
            canTransition={canTransition}
            dragging={draggingId === card.id}
            onDragStart={() => onDragStart(card.id)}
            onDragEnd={onDragEnd}
            onOpen={() => onOpen(card)}
            onMove={(target) => onMove(card, target)}
          />
        ))}
        {cards.length === 0 ? (
          <EmptyState
            compact
            title="No cases on this page"
            description="Use filters or pagination to review this status."
          />
        ) : null}
      </div>
    </section>
  );
}

function PipelineCard({
  card,
  canTransition,
  dragging,
  onDragStart,
  onDragEnd,
  onOpen,
  onMove,
}: {
  card: ReactivationCard;
  canTransition: boolean;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onOpen: () => void;
  onMove: (target: ReactivationStage) => void;
}): JSX.Element {
  const canMove = canTransition && card.available_transitions.length > 0;

  function keyboardMove(direction: -1 | 1): void {
    const current = stageIndex(card.stage);
    const ordered = card.available_transitions
      .slice()
      .sort((a, b) => stageIndex(a) - stageIndex(b));
    const target =
      direction > 0
        ? ordered.find((stage) => stageIndex(stage) > current)
        : ordered
            .slice()
            .reverse()
            .find((stage) => stageIndex(stage) < current);
    if (target) onMove(target);
  }

  return (
    <article
      tabIndex={0}
      draggable={canMove}
      onDragStart={canMove ? onDragStart : undefined}
      onDragEnd={canMove ? onDragEnd : undefined}
      onKeyDown={(event) => {
        if (event.key === "Enter") onOpen();
        if (canMove && event.altKey && event.key === "ArrowRight") {
          event.preventDefault();
          keyboardMove(1);
        }
        if (canMove && event.altKey && event.key === "ArrowLeft") {
          event.preventDefault();
          keyboardMove(-1);
        }
      }}
      className={`group rounded-surface border border-border bg-surface p-3 shadow-sm outline-none transition hover:border-accent focus-visible:ring-2 focus-visible:ring-focus ${
        canMove ? "cursor-grab" : ""
      } ${dragging ? "opacity-50" : ""}`}
      aria-label={`${card.contact_name}, ${REACTIVATION_STAGE_LABELS[card.stage]}`}
    >
      <div className="flex items-start gap-2">
        <GripVertical
          aria-hidden
          className={`mt-0.5 h-4 w-4 shrink-0 ${canMove ? "text-text-disabled" : "text-transparent"}`}
        />
        <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left">
          <span className="block truncate text-sm font-semibold text-text-primary group-hover:text-accent">
            {card.contact_name}
          </span>
          <span className="mt-0.5 block text-xs text-text-secondary">{card.contact_phone}</span>
        </button>
        {card.sla_status === "breached" ? (
          <AlertTriangle aria-label="SLA breached" className="h-4 w-4 shrink-0 text-danger" />
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {card.labels.map((label) => (
          <Badge
            key={label}
            tone={label === "priority" ? "danger" : label === "follow_up" ? "info" : "neutral"}
          >
            <Tag aria-hidden className="mr-1 h-3 w-3" />
            {REACTIVATION_LABEL_NAMES[label]}
          </Badge>
        ))}
        <WorkRiskBadges card={card} />
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-2 gap-y-2 border-t border-border pt-2 text-[11px]">
        <div>
          <dt className="text-text-disabled">Owner</dt>
          <dd className="truncate font-medium text-text-secondary">
            {card.owner_name ?? "Unassigned"}
          </dd>
        </div>
        <div>
          <dt className="text-text-disabled">Documents</dt>
          <dd className="font-medium text-text-secondary">
            {card.verified_document_count}/{card.document_count} verified
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-text-disabled">Next task</dt>
          <dd className="truncate font-medium text-text-secondary">
            {card.next_task_due_at ? formatDateTime(card.next_task_due_at) : "No open task due"}
          </dd>
        </div>
      </dl>
    </article>
  );
}

function WorkRiskBadges({ card }: { card: ReactivationCard }): JSX.Element {
  return (
    <>
      {card.reminder_view === "overdue" ? (
        <Badge tone="danger">Overdue</Badge>
      ) : card.reminder_view === "due_today" ? (
        <Badge tone="warning">Due today</Badge>
      ) : card.reminder_view === "upcoming" ? (
        <Badge tone="info">Upcoming</Badge>
      ) : null}
      {card.sla_status === "breached" ? (
        <Badge tone="danger">
          <ShieldAlert aria-hidden className="mr-1 h-3 w-3" />
          SLA breached
        </Badge>
      ) : card.sla_status === "on_track" ? (
        <Badge tone="success">SLA on track</Badge>
      ) : null}
    </>
  );
}

function PipelineList({
  cards,
  onOpen,
  onMove,
  canTransition,
}: {
  cards: ReactivationCard[];
  onOpen: (card: ReactivationCard) => void;
  onMove: (card: ReactivationCard, stage: ReactivationStage) => void;
  canTransition: boolean;
}): JSX.Element {
  return (
    <Card className="overflow-hidden" padding={false}>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase tracking-wide text-text-secondary">
            <tr>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Work priority</th>
              <th className="px-4 py-3">Owner</th>
              <th className="px-4 py-3">Next action</th>
              <th className="px-4 py-3">Move</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {cards.map((card) => (
              <tr key={card.id} className="hover:bg-hover">
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onOpen(card)}
                    className="font-semibold text-text-primary hover:text-accent"
                  >
                    {card.contact_name}
                  </button>
                  <p className="mt-0.5 text-xs text-text-secondary">{card.contact_phone}</p>
                </td>
                <td className="px-4 py-3">
                  <Badge>{REACTIVATION_STAGE_LABELS[card.stage]}</Badge>
                  <div className="mt-1 flex max-w-56 flex-wrap gap-1">
                    {card.labels.slice(0, 2).map((label) => (
                      <Badge
                        key={label}
                        tone={label === "priority" ? "danger" : "neutral"}
                      >
                        {REACTIVATION_LABEL_NAMES[label]}
                      </Badge>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex max-w-56 flex-wrap gap-1">
                    <WorkRiskBadges card={card} />
                    {card.overdue_task_count > 0 ? (
                      <Badge tone="danger">{card.overdue_task_count} overdue tasks</Badge>
                    ) : null}
                  </div>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {card.owner_name ?? "Unassigned"}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  <span className="block">
                    {card.next_task_due_at ? formatDateTime(card.next_task_due_at) : "No task due"}
                  </span>
                  <span className="mt-1 block text-xs text-text-disabled">
                    {card.verified_document_count}/{card.document_count} documents verified
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Select
                    aria-label={`Move ${card.contact_name}`}
                    controlSize="sm"
                    disabled={!canTransition || card.available_transitions.length === 0}
                    defaultValue=""
                    onChange={(event) => {
                      if (event.target.value) {
                        onMove(card, event.target.value as ReactivationStage);
                      }
                      event.target.value = "";
                    }}
                    className="w-40"
                  >
                    <option value="">Move…</option>
                    {card.available_transitions.map((target) => (
                      <option key={target} value={target}>
                        {REACTIVATION_STAGE_LABELS[target]}
                      </option>
                    ))}
                  </Select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-border md:hidden">
        {cards.map((card) => (
          <button
            key={card.id}
            type="button"
            onClick={() => onOpen(card)}
            className="flex min-h-20 w-full items-start justify-between gap-3 p-4 text-left hover:bg-hover"
          >
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-text-primary">
                {card.contact_name}
              </span>
              <span className="mt-1 block text-xs text-text-secondary">
                {REACTIVATION_STAGE_LABELS[card.stage]} · {card.owner_name ?? "Unassigned"}
              </span>
              <span className="mt-1 block truncate text-[11px] text-text-disabled">
                {card.next_task_due_at
                  ? `Next task ${formatDateTime(card.next_task_due_at)}`
                  : "No open task due"}
              </span>
            </span>
            <span className="flex max-w-28 shrink-0 flex-col items-end gap-1">
              <WorkRiskBadges card={card} />
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  detail,
  tone = "neutral",
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  detail: string;
  tone?: "neutral" | "success" | "danger" | "warning";
  active: boolean;
  onClick: () => void;
}): JSX.Element {
  const toneClass =
    tone === "success"
      ? "bg-surface-2 text-success"
      : tone === "danger"
        ? "bg-surface-2 text-danger"
        : tone === "warning"
          ? "bg-surface-2 text-warning"
          : "bg-accent-soft text-accent";

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`flex min-h-24 items-center gap-3 rounded-surface border bg-surface p-4 text-left shadow-sm transition hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
        active ? "border-accent ring-1 ring-focus/20" : "border-border"
      }`}
    >
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-control ${toneClass}`}
      >
        <Icon aria-hidden className="h-5 w-5" />
      </span>
      <span className="min-w-0">
        <span className="block text-xl font-bold text-text-primary">{value}</span>
        <span className="block text-xs font-semibold text-text-secondary">{label}</span>
        <span className="mt-0.5 block truncate text-[11px] text-text-disabled">{detail}</span>
      </span>
    </button>
  );
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown date";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function PipelineLoading(): JSX.Element {
  return (
    <div aria-label="Loading reactivation pipeline" className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-44 w-full" />
      <div className="flex gap-3 overflow-hidden">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-[26rem] w-72 shrink-0" />
        ))}
      </div>
    </div>
  );
}
