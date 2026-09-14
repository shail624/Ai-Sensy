import {
  CalendarClock,
  Clock3,
  Download,
  Pencil,
  Pause,
  Play,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import {
  apiErrorMessage,
  useCreateReportSchedule,
  useDeleteReportSchedule,
  useReportSchedules,
  useUpdateReportSchedule,
} from "@/features/analytics/api";
import {
  REPORTS,
  SCHEDULE_CADENCES,
  SCHEDULE_FORMATS,
  SCHEDULE_GRANULARITIES,
  SCHEDULE_PRESETS,
  WEEKDAYS,
  type ReportSchedule,
  type ReportScheduleCreate,
  type ReportScheduleUpdate,
} from "@/features/analytics/types";
import { useHasPermission } from "@/lib/auth";

const FIELD_CLASS =
  "h-10 w-full rounded-control border border-border bg-surface px-3 text-sm text-text-primary outline-none transition focus:border-accent focus:ring-2 focus:ring-focus";

function localTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

function blankDefinition(): ReportScheduleCreate {
  return {
    name: "",
    report: "messages",
    format: "pdf",
    preset: "last_30d",
    granularity: "day",
    cadence: "weekly",
    timezone: localTimezone(),
    local_time: "09:00",
    weekday: "monday",
    month_day: null,
    is_active: true,
  };
}

function definitionOf(row: ReportSchedule): ReportScheduleCreate {
  return {
    name: row.name,
    report: row.report,
    format: row.format,
    preset: row.preset,
    granularity: row.granularity,
    cadence: row.cadence,
    timezone: row.timezone,
    local_time: row.local_time,
    weekday: row.weekday ?? null,
    month_day: row.month_day ?? null,
    is_active: row.is_active,
  };
}

function updateOf(row: ReportSchedule, changes: Partial<ReportScheduleCreate> = {}): ReportScheduleUpdate {
  return { ...definitionOf(row), ...changes, expected_row_version: row.row_version };
}

function displayDate(value: string | null): string {
  if (!value) return "Not scheduled";
  const utcValue = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(utcValue));
}

function cadenceLabel(row: ReportSchedule): string {
  if (row.cadence === "weekly") {
    return `Every ${row.weekday?.replace(/^./, (letter) => letter.toUpperCase())} at ${row.local_time}`;
  }
  if (row.cadence === "monthly") return `Day ${row.month_day} each month at ${row.local_time}`;
  return `Every day at ${row.local_time}`;
}

export function ReportSchedules(): JSX.Element | null {
  const canExport = useHasPermission("analytics:export");
  const canManage = useHasPermission("analytics:executive") && canExport;
  const schedules = useReportSchedules(canManage);
  const create = useCreateReportSchedule();
  const update = useUpdateReportSchedule();
  const remove = useDeleteReportSchedule();
  const [form, setForm] = useState<ReportScheduleCreate>(blankDefinition);
  const [editing, setEditing] = useState<ReportSchedule | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  if (!canManage) return null;

  const mutationError = create.error ?? update.error ?? remove.error;

  function setField<Key extends keyof ReportScheduleCreate>(
    key: Key,
    value: ReportScheduleCreate[Key],
  ): void {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function startCreate(): void {
    setEditing(null);
    setForm(blankDefinition());
    setShowForm(true);
  }

  function startEdit(row: ReportSchedule): void {
    setEditing(row);
    setForm(definitionOf(row));
    setShowForm(true);
  }

  function closeForm(): void {
    setEditing(null);
    setShowForm(false);
    setForm(blankDefinition());
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const normalized: ReportScheduleCreate = {
      ...form,
      weekday: form.cadence === "weekly" ? form.weekday || "monday" : null,
      month_day: form.cadence === "monthly" ? form.month_day || 1 : null,
    };
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          body: { ...normalized, expected_row_version: editing.row_version },
        });
      } else {
        await create.mutateAsync(normalized);
      }
      closeForm();
    } catch {
      // The mutation retains the typed API error for the inline ErrorState below.
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">Automatic delivery</p>
          <p className="mt-1 max-w-2xl text-sm text-text-secondary">
            Generate recurring evidence packs in your timezone. Completed files appear in Download
            Center and trigger a ready notification.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/downloads?category=analytics"
            className="inline-flex h-9 items-center gap-2 rounded-control border border-border bg-surface px-3 text-xs font-semibold text-text-primary hover:bg-hover"
          >
            <Download aria-hidden className="h-4 w-4" />
            View downloads
          </Link>
          <Button
            type="button"
            size="sm"
            onClick={showForm ? closeForm : startCreate}
            leftIcon={showForm ? <X aria-hidden className="h-4 w-4" /> : <Plus aria-hidden className="h-4 w-4" />}
          >
            {showForm ? "Close" : "Schedule report"}
          </Button>
        </div>
      </div>

      {showForm ? (
        <form
          onSubmit={(event) => void submit(event)}
          className="rounded-2xl border border-accent/25 bg-accent-soft/30 p-4 shadow-sm"
        >
          <div className="mb-4 flex items-center gap-2">
            <CalendarClock aria-hidden className="h-5 w-5 text-accent" />
            <h3 className="font-semibold text-text-primary">
              {editing ? `Edit ${editing.name}` : "New report schedule"}
            </h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-1 text-xs font-medium text-text-secondary sm:col-span-2">
              Schedule name
              <input
                required
                maxLength={120}
                value={form.name}
                onChange={(event) => setField("name", event.target.value)}
                placeholder="Monday leadership pack"
                className={FIELD_CLASS}
              />
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Report
              <select
                value={form.report}
                onChange={(event) => setField("report", event.target.value as ReportScheduleCreate["report"])}
                className={FIELD_CLASS}
              >
                {REPORTS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Format
              <select
                value={form.format}
                onChange={(event) => setField("format", event.target.value as ReportScheduleCreate["format"])}
                className={FIELD_CLASS}
              >
                {SCHEDULE_FORMATS.map((format) => <option key={format} value={format}>{format.toUpperCase()}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Data range
              <select
                value={form.preset}
                onChange={(event) => setField("preset", event.target.value as ReportScheduleCreate["preset"])}
                className={FIELD_CLASS}
              >
                {SCHEDULE_PRESETS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Group by
              <select
                value={form.granularity}
                onChange={(event) => setField("granularity", event.target.value as ReportScheduleCreate["granularity"])}
                className={FIELD_CLASS}
              >
                {SCHEDULE_GRANULARITIES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Repeats
              <select
                value={form.cadence}
                onChange={(event) => {
                  const cadence = event.target.value as ReportScheduleCreate["cadence"];
                  setForm((current) => ({
                    ...current,
                    cadence,
                    weekday: cadence === "weekly" ? current.weekday || "monday" : null,
                    month_day: cadence === "monthly" ? current.month_day || 1 : null,
                  }));
                }}
                className={FIELD_CLASS}
              >
                {SCHEDULE_CADENCES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            {form.cadence === "weekly" ? (
              <label className="space-y-1 text-xs font-medium text-text-secondary">
                Day
                <select
                  value={form.weekday ?? "monday"}
                  onChange={(event) => setField("weekday", event.target.value as NonNullable<ReportScheduleCreate["weekday"]>)}
                  className={FIELD_CLASS}
                >
                  {WEEKDAYS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
            ) : form.cadence === "monthly" ? (
              <label className="space-y-1 text-xs font-medium text-text-secondary">
                Day of month
                <input
                  type="number"
                  min={1}
                  max={28}
                  value={form.month_day ?? 1}
                  onChange={(event) => setField("month_day", Number(event.target.value))}
                  className={FIELD_CLASS}
                />
              </label>
            ) : <div />}
            <label className="space-y-1 text-xs font-medium text-text-secondary">
              Delivery time
              <input
                type="time"
                required
                value={form.local_time}
                onChange={(event) => setField("local_time", event.target.value)}
                className={FIELD_CLASS}
              />
            </label>
            <label className="space-y-1 text-xs font-medium text-text-secondary sm:col-span-2">
              Timezone
              <input
                required
                maxLength={64}
                value={form.timezone}
                onChange={(event) => setField("timezone", event.target.value)}
                className={FIELD_CLASS}
              />
            </label>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={closeForm}>Cancel</Button>
            <Button type="submit" size="sm" loading={create.isPending || update.isPending}>
              {editing ? "Save changes" : "Create schedule"}
            </Button>
          </div>
        </form>
      ) : null}

      {mutationError ? <ErrorState message={apiErrorMessage(mutationError)} /> : null}
      {schedules.isLoading ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {[1, 2].map((key) => <Skeleton key={key} className="h-36 rounded-2xl" />)}
        </div>
      ) : schedules.isError ? (
        <ErrorState message={apiErrorMessage(schedules.error)} onRetry={() => void schedules.refetch()} />
      ) : schedules.data?.length ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {schedules.data.map((row) => (
            <article key={row.id} className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate font-semibold text-text-primary">{row.name}</h3>
                    <Badge tone={row.is_active ? "success" : "neutral"} dot>{row.is_active ? "Active" : "Paused"}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-text-secondary">
                    {REPORTS.find((option) => option.value === row.report)?.label} · {row.format.toUpperCase()} · {cadenceLabel(row)}
                  </p>
                </div>
                <Badge tone="accent">{SCHEDULE_PRESETS.find((option) => option.value === row.preset)?.label}</Badge>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-xl bg-surface-subtle px-3 py-2.5 text-sm text-text-secondary">
                <Clock3 aria-hidden className="h-4 w-4 text-accent" />
                <span>Next: <strong className="font-medium text-text-primary">{displayDate(row.next_run_at)}</strong></span>
              </div>
              <div className="mt-3 flex flex-wrap justify-end gap-1">
                <Button type="button" variant="ghost" size="sm" onClick={() => startEdit(row)} leftIcon={<Pencil aria-hidden className="h-3.5 w-3.5" />}>Edit</Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  loading={update.isPending && update.variables?.id === row.id}
                  onClick={() => update.mutate({ id: row.id, body: updateOf(row, { is_active: !row.is_active }) })}
                  leftIcon={row.is_active ? <Pause aria-hidden className="h-3.5 w-3.5" /> : <Play aria-hidden className="h-3.5 w-3.5" />}
                >
                  {row.is_active ? "Pause" : "Resume"}
                </Button>
                {confirmDelete === row.id ? (
                  <>
                    <Button type="button" variant="ghost" size="sm" onClick={() => setConfirmDelete(null)}>Keep</Button>
                    <Button
                      type="button"
                      variant="danger"
                      size="sm"
                      loading={remove.isPending}
                      onClick={() => remove.mutate({ id: row.id, rowVersion: row.row_version }, { onSuccess: () => setConfirmDelete(null) })}
                    >Delete now</Button>
                  </>
                ) : (
                  <Button type="button" variant="ghost" size="sm" onClick={() => setConfirmDelete(row.id)} leftIcon={<Trash2 aria-hidden className="h-3.5 w-3.5" />}>Delete</Button>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          compact
          title="No scheduled reports yet"
          description="Create a recurring PDF, spreadsheet, or CSV pack for your operating rhythm."
          icon={<CalendarClock aria-hidden className="h-6 w-6" />}
          action={<Button type="button" size="sm" onClick={startCreate}>Schedule first report</Button>}
        />
      )}
    </div>
  );
}
