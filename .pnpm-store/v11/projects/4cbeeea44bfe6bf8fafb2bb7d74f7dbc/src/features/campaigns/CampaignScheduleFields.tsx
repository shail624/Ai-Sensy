import type { ScheduleDraft } from "@/features/campaigns/scheduleForm";
import { MAX_DRIP_STEPS } from "@/features/campaigns/scheduleForm";
import type { ScheduleType } from "@/features/campaigns/types";
import { SCHEDULE_TYPE_LABELS } from "@/features/campaigns/types";

const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft";
const LABEL_CLASS = "mb-1.5 block text-sm font-semibold text-text-primary";

const SCHEDULE_TYPES: ScheduleType[] = ["one_time", "recurring", "drip"];

interface Props {
  draft: ScheduleDraft;
  onChange: (next: ScheduleDraft) => void;
  /** Prefix for input ids, so the fields can appear twice on one page without colliding. */
  idPrefix?: string;
}

/**
 * The three schedule shapes of FR-CAM-03/04, as one decision — "when" — with the fields that do not
 * apply simply absent. Shared by the create wizard and the detail page's schedule dialog, so a
 * schedule is expressed the same way wherever it is set.
 */
export function CampaignScheduleFields({
  draft,
  onChange,
  idPrefix = "schedule",
}: Props): JSX.Element {
  function set<K extends keyof ScheduleDraft>(key: K, value: ScheduleDraft[K]): void {
    onChange({ ...draft, [key]: value });
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`${idPrefix}-type`} className={LABEL_CLASS}>
            Schedule
          </label>
          <select
            id={`${idPrefix}-type`}
            value={draft.schedule_type}
            onChange={(event) => set("schedule_type", event.target.value as ScheduleType)}
            className={FIELD_CLASS}
          >
            {SCHEDULE_TYPES.map((type) => (
              <option key={type} value={type}>
                {SCHEDULE_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${idPrefix}-timezone`} className={LABEL_CLASS}>
            Timezone
          </label>
          <input
            id={`${idPrefix}-timezone`}
            value={draft.timezone}
            onChange={(event) => set("timezone", event.target.value)}
            placeholder="Asia/Kolkata"
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            An IANA zone name. The schedule is read in this zone.
          </p>
        </div>
      </div>

      {draft.schedule_type === "one_time" ? (
        <div>
          <label htmlFor={`${idPrefix}-run-at`} className={LABEL_CLASS}>
            Send at
          </label>
          <input
            id={`${idPrefix}-run-at`}
            type="datetime-local"
            value={draft.run_at}
            onChange={(event) => set("run_at", event.target.value)}
            className={FIELD_CLASS}
          />
        </div>
      ) : null}

      {draft.schedule_type === "recurring" ? (
        <>
          <div>
            <label htmlFor={`${idPrefix}-cron`} className={LABEL_CLASS}>
              Repeat (cron)
            </label>
            <input
              id={`${idPrefix}-cron`}
              value={draft.cron_expr}
              onChange={(event) => set("cron_expr", event.target.value)}
              placeholder="0 10 * * *"
              className={`${FIELD_CLASS} font-mono`}
            />
            <p className="mt-1 text-xs text-text-disabled">
              Five fields: minute hour day-of-month month day-of-week. `0 10 * * *` is every day at
              10:00.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor={`${idPrefix}-starts-on`} className={LABEL_CLASS}>
                First day (optional)
              </label>
              <input
                id={`${idPrefix}-starts-on`}
                type="date"
                value={draft.starts_on}
                onChange={(event) => set("starts_on", event.target.value)}
                className={FIELD_CLASS}
              />
            </div>
            <div>
              <label htmlFor={`${idPrefix}-ends-on`} className={LABEL_CLASS}>
                Last day (optional)
              </label>
              <input
                id={`${idPrefix}-ends-on`}
                type="date"
                value={draft.ends_on}
                onChange={(event) => set("ends_on", event.target.value)}
                className={FIELD_CLASS}
              />
            </div>
          </div>
        </>
      ) : null}

      {draft.schedule_type === "drip" ? (
        <>
          <div>
            <label htmlFor={`${idPrefix}-starts-at`} className={LABEL_CLASS}>
              Sequence starts
            </label>
            <input
              id={`${idPrefix}-starts-at`}
              type="datetime-local"
              value={draft.starts_at}
              onChange={(event) => set("starts_at", event.target.value)}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor={`${idPrefix}-steps`} className={LABEL_CLASS}>
              Step offsets (minutes from the start)
            </label>
            <input
              id={`${idPrefix}-steps`}
              value={draft.steps}
              onChange={(event) => set("steps", event.target.value)}
              placeholder="0, 1440, 4320"
              className={`${FIELD_CLASS} font-mono`}
            />
            <p className="mt-1 text-xs text-text-disabled">
              Each offset becomes one send. `0, 1440, 4320` is now, then a day later, then three
              days after that. Up to {MAX_DRIP_STEPS} steps.
            </p>
          </div>
        </>
      ) : null}
    </div>
  );
}
