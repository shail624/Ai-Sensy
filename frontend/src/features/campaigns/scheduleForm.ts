import type { CampaignScheduleRequest, ScheduleType } from "@/features/campaigns/types";

/** Upper bound the server enforces on a drip sequence (`MAX_DRIP_STEPS`). */
export const MAX_DRIP_STEPS = 50;

/**
 * The schedule form's own draft shape.
 *
 * Held apart from the campaign form because it posts to a different endpoint against an already
 * created campaign (`POST /campaigns/{id}/schedule`), and because its inputs are strings from
 * `datetime-local`/`date` controls rather than the instants the contract takes.
 */
export interface ScheduleDraft {
  schedule_type: ScheduleType;
  timezone: string;
  /** `datetime-local`, local time. */
  run_at: string;
  cron_expr: string;
  starts_on: string;
  ends_on: string;
  starts_at: string;
  /** Comma-separated minute offsets, as typed. */
  steps: string;
}

/** The browser's IANA zone, falling back to UTC — the same default the contract carries. */
export function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function blankSchedule(): ScheduleDraft {
  return {
    schedule_type: "one_time",
    timezone: browserTimezone(),
    run_at: "",
    cron_expr: "0 10 * * *",
    starts_on: "",
    ends_on: "",
    starts_at: "",
    steps: "0, 1440, 4320",
  };
}

/** Minute offsets from the drip anchor, in the order typed, ignoring empty entries. */
export function parseSteps(raw: string): number[] {
  return raw
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry !== "")
    .map((entry) => Number.parseInt(entry, 10));
}

/**
 * The first thing wrong with this draft, or `null`.
 *
 * Mirrors the server's own checks (`ScheduleInvalid`) so the operator is told before a round trip.
 * The server re-validates everything — including the cron grammar, which is Celery's parser and is
 * deliberately **not** reimplemented here — and its 422 is what decides.
 */
export function validateSchedule(draft: ScheduleDraft): string | null {
  if (draft.timezone.trim() === "") return "Choose a timezone.";

  if (draft.schedule_type === "one_time") {
    if (!draft.run_at) return "A one-time schedule needs a date and time.";
    if (Date.parse(draft.run_at) <= Date.now()) return "The send time must be in the future.";
    return null;
  }

  if (draft.schedule_type === "recurring") {
    const fields = draft.cron_expr.trim().split(/\s+/).filter(Boolean);
    if (fields.length !== 5) {
      return "A cron expression needs 5 fields: minute hour day-of-month month day-of-week.";
    }
    if (draft.starts_on && draft.ends_on && draft.ends_on < draft.starts_on) {
      return "The end date cannot precede the start date.";
    }
    return null;
  }

  if (!draft.starts_at) return "A drip sequence needs a start date and time.";
  const steps = parseSteps(draft.steps);
  if (steps.length === 0) return "A drip sequence needs at least one step offset.";
  if (steps.some((step) => Number.isNaN(step))) return "Step offsets must be whole numbers.";
  if (steps.length > MAX_DRIP_STEPS) return `A drip sequence is limited to ${MAX_DRIP_STEPS} steps.`;
  if (steps.some((step) => step < 0)) return "Step offsets cannot be negative.";
  if (new Set(steps).size !== steps.length) return "Step offsets must be distinct.";
  return null;
}

/** Only the fields the chosen shape uses are sent; the rest are simply absent (Doc 04 §17). */
export function toScheduleRequest(draft: ScheduleDraft): CampaignScheduleRequest {
  const base = { schedule_type: draft.schedule_type, timezone: draft.timezone };

  if (draft.schedule_type === "one_time") {
    return { ...base, run_at: new Date(draft.run_at).toISOString() };
  }
  if (draft.schedule_type === "recurring") {
    return {
      ...base,
      cron_expr: draft.cron_expr.trim(),
      starts_on: draft.starts_on || null,
      ends_on: draft.ends_on || null,
    };
  }
  return {
    ...base,
    starts_at: new Date(draft.starts_at).toISOString(),
    steps: parseSteps(draft.steps),
  };
}
