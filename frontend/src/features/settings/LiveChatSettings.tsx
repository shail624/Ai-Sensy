import { Pencil } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useInboxOperations,
  useOrganization,
  useUpdateInboxOperations,
  useUpdateOrganization,
} from "@/features/settings/api";
import {
  ConfigureDialog,
  MANAGE_CARD,
  MANAGE_FIELD,
  MANAGE_OUTLINE,
  MANAGE_PRIMARY,
  ResponsePreview,
  Toggle,
} from "@/features/settings/managePrimitives";
import type { InboxOperationsPolicy, InboxOperationsUpdate, WorkingDay } from "@/features/settings/types";
import { defaultWorkingDays } from "@/features/settings/WorkingHoursEditor";

/** Every IANA zone the browser knows, so only a real timezone can be chosen. */
const TIMEZONES: string[] =
  typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : ["Asia/Kolkata", "UTC"];

const SHORT_DAY: Record<WorkingDay["day"], string> = {
  monday: "Mon",
  tuesday: "Tue",
  wednesday: "Wed",
  thursday: "Thu",
  friday: "Fri",
  saturday: "Sat",
  sunday: "Sun",
};

type Draft = Required<Pick<InboxOperationsUpdate, "assignment_mode" | "auto_mark_read" | "send_read_receipts" | "show_typing_indicators">> & {
  consent: InboxOperationsUpdate["consent"];
  working_hours: { enabled: boolean; days: WorkingDay[] };
  automatic_replies: { welcome_enabled: boolean; welcome_body: string; off_hours_enabled: boolean; off_hours_body: string };
  auto_resolve: { enabled: boolean; inactive_after_hours: number };
};

function fromPolicy(policy: InboxOperationsPolicy): Draft {
  return {
    assignment_mode: policy.assignment_mode,
    auto_mark_read: policy.auto_mark_read,
    send_read_receipts: policy.send_read_receipts,
    show_typing_indicators: policy.show_typing_indicators ?? false,
    consent: policy.consent,
    working_hours: {
      enabled: policy.working_hours?.enabled ?? false,
      days: policy.working_hours?.days?.length ? policy.working_hours.days : defaultWorkingDays(),
    },
    automatic_replies: {
      welcome_enabled: policy.automatic_replies?.welcome_enabled ?? false,
      welcome_body: policy.automatic_replies?.welcome_body ?? "",
      off_hours_enabled: policy.automatic_replies?.off_hours_enabled ?? false,
      off_hours_body: policy.automatic_replies?.off_hours_body ?? "",
    },
    auto_resolve: {
      enabled: policy.auto_resolve?.enabled ?? false,
      inactive_after_hours: policy.auto_resolve?.inactive_after_hours ?? 72,
    },
  };
}

/** The same rules the combined inbox-policy form enforces. */
export function validateLiveChat(draft: Draft): string | null {
  const hours = draft.working_hours;
  const replies = draft.automatic_replies;
  if (hours.enabled && !hours.days.some((day) => day.enabled)) return "Working hours need at least one enabled day.";
  if (hours.enabled && hours.days.some((day) => day.enabled && day.start === day.end)) {
    return "An enabled working day must have different opening and closing times.";
  }
  if (replies.welcome_enabled && !replies.welcome_body.trim()) return "An enabled welcome reply needs message text.";
  if (replies.off_hours_enabled && !hours.enabled) return "Enable working hours before enabling an off-hours reply.";
  if (replies.off_hours_enabled && !replies.off_hours_body.trim()) return "An enabled off-hours reply needs message text.";
  const wait = draft.auto_resolve.inactive_after_hours;
  if (draft.auto_resolve.enabled && (!Number.isInteger(wait) || wait < 1 || wait > 720)) {
    return "Automatic resolution must wait between 1 and 720 whole hours.";
  }
  return null;
}

function ToggleRow({ title, description, checked, onChange, disabled }: { title: string; description: string; checked: boolean; onChange: (value: boolean) => void; disabled: boolean }): JSX.Element {
  return (
    <div className="flex items-start justify-between gap-6">
      <div>
        <h3 className="text-base font-normal text-black dark:text-text-primary">{title}</h3>
        <p className="mt-4 text-sm text-[#6e6e6e] dark:text-text-secondary">{description}</p>
      </div>
      <span className="pt-1.5">
        <Toggle checked={checked} onChange={onChange} label={title} disabled={disabled} />
      </span>
    </div>
  );
}

/**
 * The reference Live Chat Settings page: auto-resolve, read behaviour, welcome and off-hours
 * replies side by side, and day-wise working hours.
 */
export function LiveChatSettings(): JSX.Element {
  const canManage = useHasPermission("settings:manage");
  const policy = useInboxOperations();
  const update = useUpdateInboxOperations();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [configuring, setConfiguring] = useState<"welcome" | "off_hours" | null>(null);
  const organization = useOrganization();
  const updateOrganization = useUpdateOrganization();

  useEffect(() => {
    if (policy.data) setDraft(fromPolicy(policy.data));
  }, [policy.data]);

  if (policy.isLoading || (!draft && !policy.isError)) return <Spinner label="Loading Live Chat settings…" />;
  if (policy.isError || !policy.data || !draft) {
    return <ErrorState message={apiErrorMessage(policy.error)} onRetry={() => void policy.refetch()} />;
  }
  const current = draft;
  const locked = !canManage || update.isPending;
  const timezone = policy.data.organization_timezone;
  // The workspace timezone lives on the organization; changing it here is the same audited update.

  function save(next: Draft = current): void {
    setDraft(next);
    const problem = validateLiveChat(next);
    setError(problem);
    if (problem) return;
    update.mutate({
      ...next,
      automatic_replies: {
        ...next.automatic_replies,
        welcome_body: next.automatic_replies.welcome_body.trim(),
        off_hours_body: next.automatic_replies.off_hours_body.trim(),
      },
    });
  }

  function setDay(day: WorkingDay): void {
    setDraft({ ...current, working_hours: { ...current.working_hours, days: current.working_hours.days.map((entry) => (entry.day === day.day ? day : entry)) } });
  }

  const replies = current.automatic_replies;

  return (
    <div className="space-y-8">
      <section aria-label="Auto Resolve Chats" className={`${MANAGE_CARD} space-y-5 px-8 py-8`}>
        <ToggleRow
          title="Auto Resolve Chats"
          description={`Automatically resolve open chats after ${current.auto_resolve.inactive_after_hours} hours without activity.`}
          checked={current.auto_resolve.enabled}
          disabled={locked}
          onChange={(enabled) => save({ ...current, auto_resolve: { ...current.auto_resolve, enabled } })}
        />
        {current.auto_resolve.enabled ? (
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="auto-resolve-hours" className="text-sm text-black dark:text-text-primary">Resolve after</label>
            <input
              id="auto-resolve-hours"
              type="number"
              min={1}
              max={720}
              value={current.auto_resolve.inactive_after_hours}
              disabled={!canManage}
              onChange={(event) => setDraft({ ...current, auto_resolve: { ...current.auto_resolve, inactive_after_hours: Number(event.target.value) } })}
              className={`${MANAGE_FIELD} h-[38px] w-24`}
            />
            <span className="text-sm text-[#6e6e6e] dark:text-text-secondary">hours</span>
            {canManage ? (
              <button type="button" onClick={() => save()} disabled={locked} className={MANAGE_PRIMARY}>Save</button>
            ) : null}
          </div>
        ) : null}
      </section>

      <section aria-label="Read and routing" className={`${MANAGE_CARD} space-y-[30px] px-8 py-[38px]`}>
        <ToggleRow
          title="Manage Read Receipts"
          description="Customers can see when their messages have been read."
          checked={current.send_read_receipts}
          disabled={locked}
          onChange={(send_read_receipts) => save({ ...current, send_read_receipts })}
        />
        <ToggleRow
          title="Show Typing Indicators"
          description={current.send_read_receipts
            ? "WhatsApp users will see typing indicators when you are preparing a response."
            : "Turn on read receipts first — WhatsApp shows typing together with a read tick."}
          checked={current.show_typing_indicators && current.send_read_receipts}
          disabled={locked || !current.send_read_receipts}
          onChange={(show_typing_indicators) => save({ ...current, show_typing_indicators })}
        />
        <ToggleRow
          title="Clear unread on open"
          description="Opening a chat clears its shared unread count. Turn off to change unread state only on purpose."
          checked={current.auto_mark_read}
          disabled={locked}
          onChange={(auto_mark_read) => save({ ...current, auto_mark_read })}
        />
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <h3 className="text-base font-normal text-black dark:text-text-primary">New chat assignment</h3>
            <p className="mt-4 text-sm text-[#6e6e6e] dark:text-text-secondary">Leave new chats unassigned, or give each to the agent with the fewest open chats.</p>
          </div>
          <select
            aria-label="Assignment rule"
            value={current.assignment_mode}
            disabled={locked}
            onChange={(event) => save({ ...current, assignment_mode: event.target.value as Draft["assignment_mode"] })}
            className={`${MANAGE_FIELD} h-[38px] pr-8`}
          >
            <option value="manual">Leave unassigned</option>
            <option value="least_open">Balance by open workload</option>
          </select>
        </div>
      </section>

      <section aria-label="Automated replies" className={`${MANAGE_CARD} grid py-6 lg:grid-cols-2`}>
        {(
          [
            ["welcome", "Welcome Message", "Configure automated reply for user's first query during working hours", replies.welcome_enabled, replies.welcome_body],
            ["off_hours", "Off Hours Message", "Configure automated reply for user's first query during off hours", replies.off_hours_enabled, replies.off_hours_body],
          ] as const
        ).map(([key, title, help, enabled, body]) => (
          <div key={key} className="px-8 py-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="flex items-center gap-4 text-base font-normal text-black dark:text-text-primary">
                  {title}
                  <Toggle
                    small
                    checked={enabled}
                    disabled={locked}
                    label={title}
                    onChange={(value) => save({ ...current, automatic_replies: { ...replies, [`${key}_enabled`]: value } })}
                  />
                </h3>
                <p className="mt-2 max-w-[274px] text-xs text-[#6e6e6e] dark:text-text-secondary">{help}</p>
              </div>
              {canManage ? (
                <button type="button" onClick={() => setConfiguring(key)} className={MANAGE_OUTLINE}>
                  <Pencil aria-hidden className="h-[18px] w-[18px]" /> Configure
                </button>
              ) : null}
            </div>
            <div className="mt-8">
              <ResponsePreview body={enabled ? body : ""} />
            </div>
          </div>
        ))}
      </section>

      <section aria-labelledby="working-hours-title" className={`${MANAGE_CARD} px-8 py-8`}>
        <h2 id="working-hours-title" className="flex items-center gap-4 text-base font-normal text-black dark:text-text-primary">
          Working Hours
          <Toggle
            small
            checked={current.working_hours.enabled}
            disabled={locked}
            label="Use working hours"
            onChange={(enabled) =>
              save({
                ...current,
                working_hours: { ...current.working_hours, enabled },
                automatic_replies: enabled ? replies : { ...replies, off_hours_enabled: false },
              })
            }
          />
        </h2>
        <p className="mt-1 text-xs text-[#6e6e6e] dark:text-text-secondary">Configure day-wise working hours for automated replies</p>

        <div className="mt-6 flex items-center gap-[35px]">
          <span className="w-[65px] text-sm text-black dark:text-text-primary">Timezone</span>
          <select
            aria-label="Timezone"
            value={timezone}
            disabled={!canManage || !organization.data || updateOrganization.isPending}
            onChange={(event) => {
              if (!organization.data) return;
              updateOrganization.mutate(
                { timezone: event.target.value, row_version: organization.data.row_version },
                { onSuccess: () => void policy.refetch() },
              );
            }}
            className={`${MANAGE_FIELD} h-10 w-[433px] max-w-full pr-8`}
          >
            {TIMEZONES.includes(timezone) ? null : <option value={timezone}>{timezone}</option>}
            {TIMEZONES.map((zone) => <option key={zone} value={zone}>{zone}</option>)}
          </select>
        </div>

        <ul className="mt-6 space-y-[10px]">
          {current.working_hours.days.map((day) => (
            <li key={day.day} className="flex flex-wrap items-center gap-3">
              <span className="w-8 text-sm text-black dark:text-text-primary">{SHORT_DAY[day.day]}</span>
              <span className="w-[44px]">
                <Toggle small checked={day.enabled} disabled={!canManage || !current.working_hours.enabled} label={`${SHORT_DAY[day.day]} open`} onChange={(enabled) => setDay({ ...day, enabled })} />
              </span>
              {day.enabled ? (
                <>
                  <input
                    type="time"
                    aria-label={`${SHORT_DAY[day.day]} opens`}
                    value={day.start}
                    disabled={!canManage || !current.working_hours.enabled}
                    onChange={(event) => setDay({ ...day, start: event.target.value })}
                    className={`${MANAGE_FIELD} h-[38px] w-[197px]`}
                  />
                  <span className="text-sm text-[#6e6e6e]">To</span>
                  <input
                    type="time"
                    aria-label={`${SHORT_DAY[day.day]} closes`}
                    value={day.end}
                    disabled={!canManage || !current.working_hours.enabled}
                    onChange={(event) => setDay({ ...day, end: event.target.value })}
                    className={`${MANAGE_FIELD} h-[38px] w-[197px]`}
                  />
                </>
              ) : (
                <span className="pl-[172px] text-sm text-[#bdbdbd]">Closed</span>
              )}
            </li>
          ))}
        </ul>
        {canManage ? (
          <button type="button" onClick={() => save()} disabled={locked} className={`${MANAGE_PRIMARY} mt-8`}>
            {update.isPending ? "Saving…" : "Save Working Hours"}
          </button>
        ) : null}
      </section>

      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      {update.error ? <ErrorState message={apiErrorMessage(update.error)} /> : null}
      {updateOrganization.error ? <ErrorState message={apiErrorMessage(updateOrganization.error)} /> : null}
      {update.isSuccess && !error ? <p role="status" className="text-sm text-success-on-soft">Settings saved.</p> : null}
      {!canManage ? <p className="text-sm text-text-secondary">Read-only — changing Live Chat settings needs settings:manage.</p> : null}

      {configuring ? (
        <ConfigureDialog
          description={configuring === "welcome"
            ? "Sent once to a customer's first message during working hours."
            : "Sent once to a customer's first message outside working hours."}
          switchLabel={configuring === "welcome" ? "Send welcome message" : "Send off hours message"}
          enabled={configuring === "welcome" ? replies.welcome_enabled : replies.off_hours_enabled}
          body={configuring === "welcome" ? replies.welcome_body : replies.off_hours_body}
          onClose={() => setConfiguring(null)}
          onSave={(enabled, body) =>
            save({
              ...current,
              automatic_replies: configuring === "welcome"
                ? { ...replies, welcome_enabled: enabled, welcome_body: body }
                : { ...replies, off_hours_enabled: enabled, off_hours_body: body },
            })
          }
        />
      ) : null}
    </div>
  );
}
