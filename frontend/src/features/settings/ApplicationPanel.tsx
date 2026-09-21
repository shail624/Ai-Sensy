import { CheckCheck, MessageSquareText, Route, Save, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  Badge,
  Button,
  DefinitionRow,
  ErrorState,
  Field,
  Input,
  Section,
  Select,
  Spinner,
} from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useInboxOperations,
  useSettings,
  useUpdateInboxOperations,
  useUpdateSettings,
} from "@/features/settings/api";
import { AutoResolveEditor } from "@/features/settings/AutoResolveEditor";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";
import {
  defaultWorkingDays,
  WorkingHoursEditor,
} from "@/features/settings/WorkingHoursEditor";
import type {
  InboxOperationsPolicy,
  InboxOperationsUpdate,
  Setting,
  WorkingDay,
} from "@/features/settings/types";
import {
  isEditableSetting,
  SCOPE_EXPLANATIONS,
  SCOPE_LABELS,
  SCOPE_ORGANIZATION,
  SCOPE_SYSTEM,
} from "@/features/settings/types";
import { formatCount } from "@/lib/format";

interface OperationsDraft {
  assignmentMode: "manual" | "least_open";
  autoMarkRead: boolean;
  sendReadReceipts: boolean;
  consentEnabled: boolean;
  optInKeywords: string;
  optOutKeywords: string;
  optInResponseEnabled: boolean;
  optInResponseBody: string;
  optOutResponseEnabled: boolean;
  optOutResponseBody: string;
  workingHoursEnabled: boolean;
  workingDays: WorkingDay[];
  welcomeEnabled: boolean;
  welcomeBody: string;
  offHoursEnabled: boolean;
  offHoursBody: string;
  autoResolveEnabled: boolean;
  inactiveAfterHours: number;
}

const DEFAULT_DRAFT: OperationsDraft = {
  assignmentMode: "manual",
  autoMarkRead: true,
  sendReadReceipts: true,
  consentEnabled: false,
  optInKeywords: "START, YES",
  optOutKeywords: "STOP, UNSUBSCRIBE",
  optInResponseEnabled: false,
  optInResponseBody: "",
  optOutResponseEnabled: false,
  optOutResponseBody: "",
  workingHoursEnabled: false,
  workingDays: defaultWorkingDays(),
  welcomeEnabled: false,
  welcomeBody: "",
  offHoursEnabled: false,
  offHoursBody: "",
  autoResolveEnabled: false,
  inactiveAfterHours: 72,
};

function policyDraft(policy: InboxOperationsPolicy | undefined): OperationsDraft {
  if (!policy) return DEFAULT_DRAFT;
  return {
    assignmentMode: policy.assignment_mode,
    autoMarkRead: policy.auto_mark_read,
    sendReadReceipts: policy.send_read_receipts,
    consentEnabled: policy.consent?.enabled ?? false,
    optInKeywords: (policy.consent?.opt_in_keywords ?? ["START", "YES"]).join(", "),
    optOutKeywords: (policy.consent?.opt_out_keywords ?? ["STOP", "UNSUBSCRIBE"]).join(", "),
    optInResponseEnabled: policy.consent?.opt_in_response_enabled ?? false,
    optInResponseBody: policy.consent?.opt_in_response_body ?? "",
    optOutResponseEnabled: policy.consent?.opt_out_response_enabled ?? false,
    optOutResponseBody: policy.consent?.opt_out_response_body ?? "",
    workingHoursEnabled: policy.working_hours?.enabled ?? false,
    workingDays: policy.working_hours?.days ?? defaultWorkingDays(),
    welcomeEnabled: policy.automatic_replies?.welcome_enabled ?? false,
    welcomeBody: policy.automatic_replies?.welcome_body ?? "",
    offHoursEnabled: policy.automatic_replies?.off_hours_enabled ?? false,
    offHoursBody: policy.automatic_replies?.off_hours_body ?? "",
    autoResolveEnabled: policy.auto_resolve?.enabled ?? false,
    inactiveAfterHours: policy.auto_resolve?.inactive_after_hours ?? 72,
  };
}

function keywordList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

function toEntry(setting: Setting, canManage: boolean): KeyValueEntry {
  const editable = canManage && isEditableSetting(setting);
  return {
    key: setting.key,
    value: setting.value,
    editable,
    secret: setting.is_secret,
    scope: SCOPE_LABELS[setting.scope] ?? setting.scope,
    updatedAt: setting.updated_at,
    readOnlyReason: setting.is_secret
      ? "Secret — the server never returns or accepts this value here."
      : setting.scope === SCOPE_SYSTEM
        ? SCOPE_EXPLANATIONS.system
        : !canManage
          ? "Read-only — changing settings needs settings:manage."
          : undefined,
  };
}

function OperationalPolicyPanel({ canManage }: { canManage: boolean }): JSX.Element {
  const { hash } = useLocation();
  const consentOnly = hash === "#consent";
  const policy = useInboxOperations();
  const update = useUpdateInboxOperations();
  const [draft, setDraft] = useState<OperationsDraft>(DEFAULT_DRAFT);
  const [validation, setValidation] = useState<string | null>(null);

  useEffect(() => {
    if (policy.data) setDraft(policyDraft(policy.data));
  }, [policy.data]);

  useEffect(() => {
    if (!policy.data || !["#consent", "#inbox-policy"].includes(hash)) return;
    const frame = requestAnimationFrame(() => {
      const target = document.getElementById(hash.slice(1));
      target?.scrollIntoView?.({ block: "start" });
      target?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [hash, policy.data]);

  function save(): void {
    const optIn = keywordList(draft.optInKeywords);
    const optOut = keywordList(draft.optOutKeywords);
    if (draft.consentEnabled && (!optIn.length || !optOut.length)) {
      setValidation("Enabled consent handling needs at least one opt-in and one opt-out keyword.");
      return;
    }
    const normalizedIn = new Set(optIn.map((keyword) => keyword.toUpperCase()));
    const overlap = optOut.find((keyword) => normalizedIn.has(keyword.toUpperCase()));
    if (overlap) {
      setValidation(`“${overlap}” cannot be both an opt-in and opt-out keyword.`);
      return;
    }
    if (draft.optInResponseEnabled && !draft.optInResponseBody.trim()) {
      setValidation("An enabled opt-in response needs message text.");
      return;
    }
    if (draft.optOutResponseEnabled && !draft.optOutResponseBody.trim()) {
      setValidation("An enabled opt-out response needs message text.");
      return;
    }
    if (draft.workingHoursEnabled && !draft.workingDays.some((day) => day.enabled)) {
      setValidation("Working hours need at least one enabled day.");
      return;
    }
    const zeroLengthDay = draft.workingDays.find(
      (day) => draft.workingHoursEnabled && day.enabled && day.start === day.end,
    );
    if (zeroLengthDay) {
      setValidation("An enabled working day must have different opening and closing times.");
      return;
    }
    if (draft.welcomeEnabled && !draft.welcomeBody.trim()) {
      setValidation("An enabled welcome reply needs message text.");
      return;
    }
    if (draft.offHoursEnabled && !draft.workingHoursEnabled) {
      setValidation("Enable working hours before enabling an off-hours reply.");
      return;
    }
    if (draft.offHoursEnabled && !draft.offHoursBody.trim()) {
      setValidation("An enabled off-hours reply needs message text.");
      return;
    }
    if (
      draft.autoResolveEnabled &&
      (!Number.isInteger(draft.inactiveAfterHours) ||
        draft.inactiveAfterHours < 1 ||
        draft.inactiveAfterHours > 720)
    ) {
      setValidation("Automatic resolution must wait between 1 and 720 whole hours.");
      return;
    }
    setValidation(null);
    const body: InboxOperationsUpdate = {
      assignment_mode: draft.assignmentMode,
      auto_mark_read: draft.autoMarkRead,
      send_read_receipts: draft.sendReadReceipts,
      consent: {
        enabled: draft.consentEnabled,
        opt_in_keywords: optIn,
        opt_out_keywords: optOut,
        opt_in_response_enabled: draft.optInResponseEnabled,
        opt_in_response_body: draft.optInResponseBody.trim(),
        opt_out_response_enabled: draft.optOutResponseEnabled,
        opt_out_response_body: draft.optOutResponseBody.trim(),
      },
      working_hours: {
        enabled: draft.workingHoursEnabled,
        days: draft.workingDays,
      },
      automatic_replies: {
        welcome_enabled: draft.welcomeEnabled,
        welcome_body: draft.welcomeBody.trim(),
        off_hours_enabled: draft.offHoursEnabled,
        off_hours_body: draft.offHoursBody.trim(),
      },
      auto_resolve: {
        enabled: draft.autoResolveEnabled,
        inactive_after_hours: draft.inactiveAfterHours,
      },
    };
    update.mutate(body);
  }

  if (policy.isLoading) return <Spinner label="Loading inbox operations…" />;
  if (policy.isError) {
    return (
      <ErrorState message={apiErrorMessage(policy.error)} onRetry={() => void policy.refetch()} />
    );
  }

  return (
    <div id="inbox-policy" tabIndex={-1} className="scroll-mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
    <Section
      title={consentOnly ? "Consent keyword rules" : "Inbox operations"}
      description={consentOnly
        ? "Control the exact messages that record customer opt-in and opt-out choices."
        : "Organization-wide rules consumed by new conversations and inbound messages."}
      icon={consentOnly
        ? <ShieldCheck aria-hidden className="h-4 w-4" />
        : <SlidersHorizontal aria-hidden className="h-4 w-4" />}
      action={
        <Badge tone={policy.data?.configured ? "success" : "neutral"}>
          {policy.data?.configured ? "Configured" : "Using safe defaults"}
        </Badge>
      }
    >
      {!consentOnly ? <div className="grid gap-4 xl:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface-2 p-4">
          <div className="mb-3 flex items-start gap-3">
            <Route aria-hidden className="mt-0.5 h-4 w-4 text-accent" />
            <div>
              <h4 className="text-sm font-semibold text-text-primary">New conversation routing</h4>
              <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">
                Choose whether new threads wait unassigned or go to the eligible teammate with the
                fewest unresolved conversations.
              </p>
            </div>
          </div>
          <Field htmlFor="assignment-mode" label="Assignment rule">
            <Select
              id="assignment-mode"
              value={draft.assignmentMode}
              disabled={!canManage}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  assignmentMode: event.target.value as OperationsDraft["assignmentMode"],
                }))
              }
            >
              <option value="manual">Leave unassigned</option>
              <option value="least_open">Balance by open workload</option>
            </Select>
          </Field>
        </div>

        <label className="flex min-h-40 cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface-2 p-4 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus">
          <input
            type="checkbox"
            aria-label="Clear unread on open"
            checked={draft.autoMarkRead}
            disabled={!canManage}
            onChange={(event) =>
              setDraft((current) => ({ ...current, autoMarkRead: event.target.checked }))
            }
            className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
          />
          <span>
            <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <CheckCheck aria-hidden className="h-4 w-4 text-accent" />
              Clear unread on open
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
              Opening a conversation clears its shared unread counter. Turn this off when teams
              want unread state changed only by a deliberate action.
            </span>
          </span>
        </label>

        <label className="flex min-h-40 cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface-2 p-4 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus">
          <input
            type="checkbox"
            aria-label="Send read receipts to customers"
            checked={draft.sendReadReceipts}
            disabled={!canManage}
            onChange={(event) =>
              setDraft((current) => ({ ...current, sendReadReceipts: event.target.checked }))
            }
            className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
          />
          <span>
            <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <CheckCheck aria-hidden className="h-4 w-4 text-accent" />
              Send read receipts to customers
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
              When an unread conversation is marked read, notify supported WhatsApp providers.
              Local unread state still works for connectors without this capability.
            </span>
          </span>
        </label>

        <div className="rounded-xl border border-border bg-surface-2 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              aria-label="Recognize consent keywords"
              checked={draft.consentEnabled}
              disabled={!canManage}
              onChange={(event) =>
                setDraft((current) => ({ ...current, consentEnabled: event.target.checked }))
              }
              className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
            />
            <span>
              <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                <ShieldCheck aria-hidden className="h-4 w-4 text-accent" />
                Recognize consent keywords
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                Exact text matches update the contact&apos;s opt-in state and create timeline and audit
                evidence. Sentences containing a keyword are ignored.
              </span>
            </span>
          </label>
        </div>
      </div> : null}

      {consentOnly ? <div
        id="consent"
        tabIndex={-1}
        className="scroll-mt-4 rounded-xl border border-border bg-surface-2 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus sm:p-5"
      >
        <label className="flex cursor-pointer items-start justify-between gap-4">
          <span>
            <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <ShieldCheck aria-hidden className="h-4 w-4 text-accent" />
              Recognize consent keywords
            </span>
            <span className="mt-1 block max-w-2xl text-xs leading-relaxed text-text-secondary">
              Exact whole-message matches update the contact&apos;s consent record. A sentence that merely
              contains a keyword is ignored.
            </span>
          </span>
          <input
            type="checkbox"
            aria-label="Recognize consent keywords"
            checked={draft.consentEnabled}
            disabled={!canManage}
            onChange={(event) =>
              setDraft((current) => ({ ...current, consentEnabled: event.target.checked }))
            }
            className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-accent)]"
          />
        </label>
      </div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Field
          htmlFor="opt-in-keywords"
          label="Opt-in keywords"
          description="Messages that record permission to contact this person. Separate entries with commas."
        >
          <Input
            id="opt-in-keywords"
            value={draft.optInKeywords}
            disabled={!canManage || !draft.consentEnabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, optInKeywords: event.target.value }))
            }
          />
        </Field>
        <Field
          htmlFor="opt-out-keywords"
          label="Opt-out keywords"
          description="Messages that record withdrawal. Matching ignores case and surrounding spaces."
        >
          <Input
            id="opt-out-keywords"
            value={draft.optOutKeywords}
            disabled={!canManage || !draft.consentEnabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, optOutKeywords: event.target.value }))
            }
          />
        </Field>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {(
          [
            [
              "opt-in",
              "Opt-in acknowledgement",
              draft.optInResponseEnabled,
              draft.optInResponseBody,
            ],
            [
              "opt-out",
              "Opt-out acknowledgement",
              draft.optOutResponseEnabled,
              draft.optOutResponseBody,
            ],
          ] as const
        ).map(([kind, label, enabled, body]) => (
          <div key={kind} className="rounded-xl border border-border bg-surface-2 p-4 sm:p-5">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                aria-label={`Send ${kind} acknowledgement`}
                checked={enabled}
                disabled={!canManage || !draft.consentEnabled}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    ...(kind === "opt-in"
                      ? { optInResponseEnabled: event.target.checked }
                      : { optOutResponseEnabled: event.target.checked }),
                  }))
                }
                className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
              />
              <span>
                <span className="block text-sm font-semibold text-text-primary">{label}</span>
                <span className="mt-1 block text-xs text-text-secondary">
                  Sent only after the consent change is recorded. A delivery failure never
                  reverses it.
                </span>
              </span>
            </label>
            <div className="mt-4 rounded-xl border border-border bg-surface p-3">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium text-text-secondary">
                <MessageSquareText aria-hidden className="h-4 w-4 text-accent" />
                Customer preview
              </div>
              <textarea
                aria-label={`${label} message`}
                value={body}
                maxLength={1000}
                disabled={!canManage || !draft.consentEnabled || !enabled}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    ...(kind === "opt-in"
                      ? { optInResponseBody: event.target.value }
                      : { optOutResponseBody: event.target.value }),
                  }))
                }
                className="min-h-24 w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
                placeholder="Enter the confirmation message"
              />
            </div>
            <p className="mt-1 text-right text-xs text-text-disabled">{body.length}/1,000</p>
          </div>
        ))}
      </div>

      {!consentOnly ? <WorkingHoursEditor
        disabled={!canManage}
        timezone={policy.data?.organization_timezone ?? "UTC"}
        enabled={draft.workingHoursEnabled}
        days={draft.workingDays}
        welcomeEnabled={draft.welcomeEnabled}
        welcomeBody={draft.welcomeBody}
        offHoursEnabled={draft.offHoursEnabled}
        offHoursBody={draft.offHoursBody}
        onEnabledChange={(enabled) =>
          setDraft((current) => ({
            ...current,
            workingHoursEnabled: enabled,
            offHoursEnabled: enabled ? current.offHoursEnabled : false,
          }))
        }
        onDayChange={(day) =>
          setDraft((current) => ({
            ...current,
            workingDays: current.workingDays.map((entry) =>
              entry.day === day.day ? day : entry,
            ),
          }))
        }
        onWelcomeEnabledChange={(enabled) =>
          setDraft((current) => ({ ...current, welcomeEnabled: enabled }))
        }
        onWelcomeBodyChange={(body) =>
          setDraft((current) => ({ ...current, welcomeBody: body }))
        }
        onOffHoursEnabledChange={(enabled) =>
          setDraft((current) => ({ ...current, offHoursEnabled: enabled }))
        }
        onOffHoursBodyChange={(body) =>
          setDraft((current) => ({ ...current, offHoursBody: body }))
        }
      /> : null}

      {!consentOnly ? <AutoResolveEditor
        disabled={!canManage}
        enabled={draft.autoResolveEnabled}
        inactiveAfterHours={draft.inactiveAfterHours}
        onEnabledChange={(enabled) =>
          setDraft((current) => ({ ...current, autoResolveEnabled: enabled }))
        }
        onInactiveAfterHoursChange={(hours) =>
          setDraft((current) => ({ ...current, inactiveAfterHours: hours }))
        }
      /> : null}

      {validation ? (
        <p role="alert" className="mt-3 text-xs text-danger">{validation}</p>
      ) : null}
      {update.error ? (
        <div className="mt-3"><ErrorState message={apiErrorMessage(update.error)} /></div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <p className="text-xs text-text-secondary">
          {canManage
            ? "Changes are validated, applied organization-wide and written to the audit log."
            : "Read-only — changing this policy needs settings:manage."}
        </p>
        {canManage ? (
          <Button
            type="button"
            leftIcon={<Save aria-hidden className="h-4 w-4" />}
            loading={update.isPending}
            onClick={save}
          >
            {consentOnly ? "Save consent settings" : "Save inbox policy"}
          </Button>
        ) : null}
      </div>
    </Section>
    </div>
  );
}

/** Operational policy first; the generic store remains available for advanced deployments. */
export function ApplicationPanel(): JSX.Element {
  const { hash } = useLocation();
  const consentOnly = hash === "#consent";
  const canManage = useHasPermission("settings:manage");
  const settings = useSettings();
  const update = useUpdateSettings();
  const all = useMemo(() => settings.data ?? [], [settings.data]);
  const orgEntries = useMemo(
    () =>
      all
        .filter(
          (setting) =>
            setting.scope === SCOPE_ORGANIZATION && setting.key !== "inbox.operations.v1",
        )
        .map((setting) => toEntry(setting, canManage)),
    [all, canManage],
  );
  const systemEntries = useMemo(
    () =>
      all
        .filter((setting) => setting.scope === SCOPE_SYSTEM)
        .map((setting) => toEntry(setting, canManage)),
    [all, canManage],
  );
  const secrets = all.filter((setting) => setting.is_secret).length;

  if (settings.isLoading) return <Spinner label="Loading settings…" />;
  if (settings.isError) {
    return (
      <ErrorState message={apiErrorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }

  return (
    <div className="space-y-4">
      <OperationalPolicyPanel canManage={canManage} />

      {!consentOnly ? <Section
        title="Advanced organization settings"
        description="Additional deployment-specific values that do not yet have a dedicated control."
      >
        <KeyValueEditor
          entries={orgEntries}
          onSave={(values) => update.mutate(values)}
          canEdit={canManage}
          pending={update.isPending}
          error={update.error}
          allowAdd
          emptyTitle="No advanced settings yet"
          emptyDescription="Add a deployment-specific key only when a module documents that it consumes it."
          note="The validated inbox policy is reserved and cannot be bypassed from this advanced editor."
        />
      </Section> : null}

      {!consentOnly ? <Section title="System settings">
        {systemEntries.length === 0 ? (
          <p className="text-sm text-text-disabled">
            No system-scoped settings are stored. These come from the server&apos;s own
            configuration rather than from this screen.
          </p>
        ) : (
          <KeyValueEditor
            entries={systemEntries}
            onSave={() => undefined}
            canEdit={false}
            pending={false}
            error={null}
            emptyTitle="No system settings"
            emptyDescription="None are stored."
            note="Read-only. These values are set on the server."
          />
        )}
      </Section> : null}

      {!consentOnly ? <Section title="System information">
        <dl>
          <DefinitionRow label="Settings stored">{formatCount(all.length)}</DefinitionRow>
          <DefinitionRow label="Organization-scoped">
            {formatCount(orgEntries.length)}
          </DefinitionRow>
          <DefinitionRow label="System-scoped">{formatCount(systemEntries.length)}</DefinitionRow>
          <DefinitionRow label="Secret values">{formatCount(secrets)}</DefinitionRow>
        </dl>
        <p className="mt-3 text-xs text-text-disabled">
          Secret settings are never returned. Operational inbox behavior is modelled above; other
          advanced keys only have an effect when a platform module explicitly consumes them.
        </p>
      </Section> : null}
    </div>
  );
}
