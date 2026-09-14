import { Clock3, MessageSquareText, Moon } from "lucide-react";

import { Badge, Field, Input, Textarea } from "@/components/ui";
import type { WorkingDay } from "@/features/settings/types";

export const WEEKDAYS: readonly WorkingDay["day"][] = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const DAY_LABELS: Record<WorkingDay["day"], string> = {
  monday: "Monday",
  tuesday: "Tuesday",
  wednesday: "Wednesday",
  thursday: "Thursday",
  friday: "Friday",
  saturday: "Saturday",
  sunday: "Sunday",
};

export function defaultWorkingDays(): WorkingDay[] {
  return WEEKDAYS.map((day) => ({
    day,
    enabled: day !== "saturday" && day !== "sunday",
    start: "09:00",
    end: "18:00",
  }));
}

interface Props {
  disabled: boolean;
  timezone: string;
  enabled: boolean;
  days: WorkingDay[];
  welcomeEnabled: boolean;
  welcomeBody: string;
  offHoursEnabled: boolean;
  offHoursBody: string;
  onEnabledChange: (enabled: boolean) => void;
  onDayChange: (day: WorkingDay) => void;
  onWelcomeEnabledChange: (enabled: boolean) => void;
  onWelcomeBodyChange: (body: string) => void;
  onOffHoursEnabledChange: (enabled: boolean) => void;
  onOffHoursBodyChange: (body: string) => void;
}

/** Original, responsive schedule/message editor over the generated CORE-11 policy contract. */
export function WorkingHoursEditor({
  disabled,
  timezone,
  enabled,
  days,
  welcomeEnabled,
  welcomeBody,
  offHoursEnabled,
  offHoursBody,
  onEnabledChange,
  onDayChange,
  onWelcomeEnabledChange,
  onWelcomeBodyChange,
  onOffHoursEnabledChange,
  onOffHoursBodyChange,
}: Props): JSX.Element {
  return (
    <div className="mt-6 border-t border-border pt-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-accent-soft p-2 text-accent">
            <Clock3 aria-hidden className="h-4 w-4" />
          </span>
          <div>
            <h4 className="text-sm font-semibold text-text-primary">Availability and replies</h4>
            <p className="mt-0.5 max-w-2xl text-xs leading-relaxed text-text-secondary">
              Hours use the organization timezone. Outside-hours replies take priority; welcome
              replies are sent only when a new 24-hour customer window opens.
            </p>
          </div>
        </div>
        <Badge tone="neutral">{timezone}</Badge>
      </div>

      <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface-2 p-4 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus">
        <input
          type="checkbox"
          aria-label="Use organization working hours"
          checked={enabled}
          disabled={disabled}
          onChange={(event) => onEnabledChange(event.target.checked)}
          className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
        />
        <span>
          <span className="text-sm font-semibold text-text-primary">
            Use organization working hours
          </span>
          <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
            Enabled intervals may cross midnight. Disabled days remain fully closed.
          </span>
        </span>
      </label>

      <div className="mt-3 overflow-hidden rounded-xl border border-border">
        {days.map((day) => (
          <div
            key={day.day}
            className="grid gap-3 border-b border-border bg-surface px-4 py-3 last:border-b-0 sm:grid-cols-[minmax(7rem,1fr)_minmax(8rem,0.8fr)_minmax(8rem,0.8fr)] sm:items-end"
          >
            <label className="flex min-h-10 items-center gap-2 text-sm font-medium text-text-primary">
              <input
                type="checkbox"
                aria-label={`${DAY_LABELS[day.day]} enabled`}
                checked={day.enabled}
                disabled={disabled || !enabled}
                onChange={(event) => onDayChange({ ...day, enabled: event.target.checked })}
                className="h-4 w-4 accent-[var(--color-accent)]"
              />
              {DAY_LABELS[day.day]}
            </label>
            <Field htmlFor={`${day.day}-start`} label="Opens">
              <Input
                id={`${day.day}-start`}
                type="time"
                value={day.start}
                disabled={disabled || !enabled || !day.enabled}
                onChange={(event) => onDayChange({ ...day, start: event.target.value })}
              />
            </Field>
            <Field htmlFor={`${day.day}-end`} label="Closes">
              <Input
                id={`${day.day}-end`}
                type="time"
                value={day.end}
                disabled={disabled || !enabled || !day.enabled}
                onChange={(event) => onDayChange({ ...day, end: event.target.value })}
              />
            </Field>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface-2 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              aria-label="Send a welcome reply"
              checked={welcomeEnabled}
              disabled={disabled}
              onChange={(event) => onWelcomeEnabledChange(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
            />
            <span>
              <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                <MessageSquareText aria-hidden className="h-4 w-4 text-accent" />
                Welcome reply
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                At most once when a new customer-service window opens during available hours.
              </span>
            </span>
          </label>
          <div className="mt-3">
            <Field htmlFor="welcome-reply-body" label="Message">
              <Textarea
                id="welcome-reply-body"
                rows={4}
                maxLength={1000}
                value={welcomeBody}
                disabled={disabled || !welcomeEnabled}
                onChange={(event) => onWelcomeBodyChange(event.target.value)}
              />
            </Field>
            <p className="mt-1 text-right text-xs text-text-disabled">
              {welcomeBody.length}/1,000
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface-2 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              aria-label="Send an off-hours reply"
              checked={offHoursEnabled}
              disabled={disabled || !enabled}
              onChange={(event) => onOffHoursEnabledChange(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
            />
            <span>
              <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                <Moon aria-hidden className="h-4 w-4 text-accent" />
                Off-hours reply
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                At most once per conversation in 24 hours; stale webhook replay never sends it.
              </span>
            </span>
          </label>
          <div className="mt-3">
            <Field htmlFor="off-hours-reply-body" label="Message">
              <Textarea
                id="off-hours-reply-body"
                rows={4}
                maxLength={1000}
                value={offHoursBody}
                disabled={disabled || !enabled || !offHoursEnabled}
                onChange={(event) => onOffHoursBodyChange(event.target.value)}
              />
            </Field>
            <p className="mt-1 text-right text-xs text-text-disabled">
              {offHoursBody.length}/1,000
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
