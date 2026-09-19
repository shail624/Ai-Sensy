import { Bookmark, Lock, Save, Trash2, Users, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { Button, Field, Input, Modal, Select } from "@/components/ui";
import {
  useCreateReportView,
  useDeleteReportView,
  useReportViews,
} from "@/features/analytics/api";
import type {
  AnalyticsFilterState,
  ReportView,
  ReportViewCreate,
} from "@/features/analytics/types";
import { apiErrorMessage } from "@/lib/api/errors";
import { useHasPermission } from "@/lib/auth";

interface Props {
  filters: AnalyticsFilterState;
  onApply: (filters: AnalyticsFilterState) => void;
}

function portableFilters(filters: AnalyticsFilterState): ReportViewCreate["filters"] | null {
  const common = {
    granularity: filters.granularity,
    compare: filters.compare || undefined,
  };
  if (filters.preset) return { ...common, preset: filters.preset };
  if (!filters.from || !filters.to || filters.from >= filters.to) return null;
  return { ...common, from: filters.from, to: filters.to };
}

export function ReportSavedViews({ filters, onApply }: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const views = useReportViews();
  const canManageShared = useHasPermission("analytics:views_manage");

  function apply(saved: ReportView): void {
    onApply({
      preset: saved.filters.preset ?? "",
      from: saved.filters.from ?? "",
      to: saved.filters.to ?? "",
      granularity: saved.filters.granularity,
      compare: saved.filters.compare ?? "",
    });
  }

  return (
    <>
      <div className="flex min-h-11 w-full flex-wrap items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 shadow-sm">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
          <Bookmark aria-hidden className="h-3.5 w-3.5" />
          Report views
        </span>
        {views.isLoading ? (
          <span className="text-xs text-text-disabled">Loading…</span>
        ) : views.isError ? (
          <span className="text-xs text-danger">Report views unavailable</span>
        ) : (views.data ?? []).length > 0 ? (
          <div
            aria-label="Personal and team Report views"
            className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto"
          >
            {(views.data ?? []).map((saved) => (
              <button
                key={saved.id}
                type="button"
                onClick={() => apply(saved)}
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
            Save this period and comparison for one-click reuse.
          </span>
        )}
        <Button
          variant="secondary"
          size="sm"
          leftIcon={<Save aria-hidden className="h-4 w-4" />}
          onClick={() => setOpen(true)}
        >
          Save / manage
        </Button>
      </div>

      {open ? (
        <ReportViewsDialog
          filters={portableFilters(filters)}
          views={views.data ?? []}
          canManageShared={canManageShared}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}

interface DialogProps {
  filters: ReportViewCreate["filters"] | null;
  views: ReportView[];
  canManageShared: boolean;
  onClose: () => void;
}

function ReportViewsDialog({
  filters,
  views,
  canManageShared,
  onClose,
}: DialogProps): JSX.Element {
  const [name, setName] = useState("");
  const [visibility, setVisibility] = useState<"private" | "shared">("private");
  const [pendingDelete, setPendingDelete] = useState<ReportView | null>(null);
  const createView = useCreateReportView();
  const deleteView = useDeleteReportView();

  function save(event: React.FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!name.trim() || !filters) return;
    createView.mutate(
      { name, visibility, display: "list", filters },
      { onSuccess: onClose },
    );
  }

  function confirmDelete(): void {
    if (!pendingDelete) return;
    deleteView.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) });
  }

  const privateViews = views.filter((saved) => saved.visibility === "private");
  const sharedViews = views.filter((saved) => saved.visibility === "shared");

  return (
    <Modal title="Report saved views" variant="sheet" onClose={onClose}>
      <form className="space-y-4" onSubmit={save}>
        <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
          <Field htmlFor="report-view-name" label="View name">
            <Input
              id="report-view-name"
              autoFocus
              value={name}
              maxLength={80}
              onChange={(event) => setName(event.target.value)}
              placeholder="Example: Monthly leadership"
            />
          </Field>
          <Field htmlFor="report-view-visibility" label="Visible to">
            <Select
              id="report-view-visibility"
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
        {!filters ? (
          <p role="alert" className="text-xs text-warning">
            Choose a preset or complete both custom dates before saving this view.
          </p>
        ) : null}
        {!canManageShared ? (
          <p className="text-xs text-text-disabled">
            Your role can save personal views. A Reports manager can publish team views.
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
            disabled={
              !name.trim() || !filters || (visibility === "shared" && !canManageShared)
            }
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
            This removes the saved definition only. No report, schedule or export is changed.
          </p>
          {deleteView.error ? (
            <p role="alert" className="mt-2 text-sm text-danger">
              {apiErrorMessage(deleteView.error)}
            </p>
          ) : null}
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setPendingDelete(null)}>
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
  views: ReportView[];
  onDelete: (view: ReportView) => void;
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
              <p className="min-w-0 truncate text-sm font-medium text-text-primary">
                {saved.name}
              </p>
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
