import { TimerReset } from "lucide-react";

import { Field, Input } from "@/components/ui";

interface Props {
  disabled: boolean;
  enabled: boolean;
  inactiveAfterHours: number;
  onEnabledChange: (enabled: boolean) => void;
  onInactiveAfterHoursChange: (hours: number) => void;
}

/** A deliberate, bounded control for the CORE-11 inactivity policy. */
export function AutoResolveEditor({
  disabled,
  enabled,
  inactiveAfterHours,
  onEnabledChange,
  onInactiveAfterHoursChange,
}: Props): JSX.Element {
  return (
    <div className="mt-6 border-t border-border pt-5">
      <div className="flex items-start gap-3">
        <span className="rounded-lg bg-accent-soft p-2 text-accent">
          <TimerReset aria-hidden className="h-4 w-4" />
        </span>
        <div>
          <h4 className="text-sm font-semibold text-text-primary">
            Automatic conversation resolution
          </h4>
          <p className="mt-0.5 max-w-2xl text-xs leading-relaxed text-text-secondary">
            Keep the active inbox focused by resolving read conversations after sustained
            inactivity. Unread messages, snoozed threads and conversations with open follow-up
            tasks are always protected.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 rounded-xl border border-border bg-surface-2 p-4 lg:grid-cols-[minmax(0,1fr)_12rem] lg:items-end">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            aria-label="Resolve inactive conversations"
            checked={enabled}
            disabled={disabled}
            onChange={(event) => onEnabledChange(event.target.checked)}
            className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
          />
          <span>
            <span className="text-sm font-semibold text-text-primary">
              Resolve inactive conversations
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
              A new customer message reopens the conversation automatically.
            </span>
          </span>
        </label>

        <Field
          htmlFor="auto-resolve-hours"
          label="Inactive for"
          description="1–720 hours"
        >
          <div className="relative">
            <Input
              id="auto-resolve-hours"
              type="number"
              min={1}
              max={720}
              step={1}
              value={inactiveAfterHours}
              disabled={disabled || !enabled}
              onChange={(event) => onInactiveAfterHoursChange(Number(event.target.value))}
              className="pr-14"
            />
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-text-disabled">
              hours
            </span>
          </div>
        </Field>
      </div>
    </div>
  );
}
