import { useMemo, useState } from "react";

import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useOrganization,
  useUpdateOrganization,
} from "@/features/settings/api";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";
import { formatDateTime } from "@/lib/format";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

/**
 * The organization profile (Doc 05 B11.11).
 *
 * Three fields are editable, because three is what `OrganizationUpdateRequest` accepts: name,
 * timezone and default locale. Everything else on the record — the slug, the id, the active flag —
 * is shown but not offered, because the update model has no field for it.
 *
 * There are **no branding or contact-information fields** on the organization. What exists instead
 * is a free-form `settings` object, which the PATCH does accept; it is surfaced below as the
 * schemaless store it is, rather than dressed up as a branding form the backend would not
 * understand.
 */
export function OrganizationPanel(): JSX.Element {
  const canManage = useHasPermission("settings:manage");
  const organization = useOrganization();
  const update = useUpdateOrganization();

  const [name, setName] = useState<string | null>(null);
  const [timezone, setTimezone] = useState<string | null>(null);
  const [locale, setLocale] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  const data = organization.data;

  // Local state starts as "untouched"; the record supplies the value until the operator types.
  const currentName = name ?? data?.name ?? "";
  const currentTimezone = timezone ?? data?.timezone ?? "";
  const currentLocale = locale ?? data?.default_locale ?? "";

  const settingsEntries: KeyValueEntry[] = useMemo(() => {
    const raw = (data?.settings ?? {}) as Record<string, unknown>;
    return Object.entries(raw).map(([key, value]) => ({
      key,
      value,
      editable: canManage,
      updatedAt: data?.updated_at,
    }));
  }, [data?.settings, data?.updated_at, canManage]);

  if (organization.isLoading) return <Spinner label="Loading organization…" />;

  if (organization.isError || !data) {
    return (
      <ErrorState
        message={apiErrorMessage(organization.error)}
        onRetry={() => void organization.refetch()}
      />
    );
  }

  const problems: Record<string, string> = {};
  if (currentName.trim() === "") problems.name = "Name is required";
  else if (currentName.length > 160) problems.name = "Name is too long";
  if (currentTimezone.trim() === "") problems.timezone = "Timezone is required";
  if (currentLocale.trim() === "") problems.locale = "Locale is required";

  const dirty =
    currentName !== data.name ||
    currentTimezone !== data.timezone ||
    currentLocale !== data.default_locale;

  function saveProfile(): void {
    setShowErrors(true);
    if (Object.keys(problems).length > 0 || !data) return;
    update.mutate(
      {
        name: currentName.trim(),
        timezone: currentTimezone.trim(),
        default_locale: currentLocale.trim(),
        row_version: data.row_version,
      },
      {
        onSuccess: () => {
          setName(null);
          setTimezone(null);
          setLocale(null);
          setShowErrors(false);
        },
      },
    );
  }

  function saveSettings(values: Record<string, unknown>): void {
    if (!data) return;
    // A partial merge: the PATCH replaces the whole object, so the untouched keys ride along.
    update.mutate({
      settings: { ...((data.settings ?? {}) as Record<string, unknown>), ...values },
      row_version: data.row_version,
    });
  }

  const visible = showErrors ? problems : {};

  return (
    <div className="space-y-4">
      <Section title="Profile">
        <div className="space-y-3">
          <div>
            <label htmlFor="org-name" className={LABEL_CLASS}>
              Organization name
            </label>
            <input
              id="org-name"
              value={currentName}
              disabled={!canManage}
              onChange={(event) => setName(event.target.value)}
              className={`${FIELD_CLASS} disabled:opacity-60`}
            />
            {visible.name ? <p className="text-xs text-danger">{visible.name}</p> : null}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="org-timezone" className={LABEL_CLASS}>
                Timezone
              </label>
              <input
                id="org-timezone"
                value={currentTimezone}
                disabled={!canManage}
                onChange={(event) => setTimezone(event.target.value)}
                placeholder="Asia/Kolkata"
                className={`${FIELD_CLASS} disabled:opacity-60`}
              />
              <p className="mt-1 text-xs text-text-disabled">
                An IANA zone name. Campaign schedules are read in it.
              </p>
              {visible.timezone ? <p className="text-xs text-danger">{visible.timezone}</p> : null}
            </div>
            <div>
              <label htmlFor="org-locale" className={LABEL_CLASS}>
                Default locale
              </label>
              <input
                id="org-locale"
                value={currentLocale}
                disabled={!canManage}
                onChange={(event) => setLocale(event.target.value)}
                placeholder="en"
                className={`${FIELD_CLASS} disabled:opacity-60`}
              />
              {visible.locale ? <p className="text-xs text-danger">{visible.locale}</p> : null}
            </div>
          </div>

          {update.error ? (
            <ErrorState message={apiErrorMessage(update.error)} />
          ) : null}

          {canManage ? (
            <div className="flex justify-end gap-2">
              {dirty ? (
                <button
                  type="button"
                  onClick={() => {
                    setName(null);
                    setTimezone(null);
                    setLocale(null);
                    setShowErrors(false);
                  }}
                  disabled={update.isPending}
                  className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50"
                >
                  Discard changes
                </button>
              ) : null}
              <button
                type="button"
                onClick={saveProfile}
                disabled={update.isPending || !dirty}
                className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50"
              >
                {update.isPending ? "Saving…" : "Save profile"}
              </button>
            </div>
          ) : (
            <p className="text-xs text-text-disabled">
              You can view the organization but not change it — that needs settings:manage.
            </p>
          )}
        </div>
      </Section>

      <Section title="Record">
        <dl>
          <DefinitionRow label="Slug">
            <span className="font-mono text-xs">{data.slug}</span>
          </DefinitionRow>
          <DefinitionRow label="Status">{data.is_active ? "Active" : "Inactive"}</DefinitionRow>
          <DefinitionRow label="Created">{formatDateTime(data.created_at)}</DefinitionRow>
          <DefinitionRow label="Last updated">{formatDateTime(data.updated_at)}</DefinitionRow>
          <DefinitionRow label="Organization id">
            <span className="break-all font-mono text-xs">{data.id}</span>
          </DefinitionRow>
        </dl>
        <p className="mt-3 text-xs text-text-disabled">
          The slug and status are part of the record but are not accepted by the update endpoint, so
          they are shown rather than offered. The platform stores no logo, brand colours, address or
          contact details for an organization.
        </p>
      </Section>

      <Section title="Organization settings">
        <KeyValueEditor
          entries={settingsEntries}
          onSave={saveSettings}
          canEdit={canManage}
          pending={update.isPending}
          error={update.error}
          allowAdd
          emptyTitle="No organization settings"
          emptyDescription="This organization has no custom settings stored against it."
          note="A free-form store on the organization record. Nothing in the platform reads these keys today — they are available for configuration a future module defines."
        />
      </Section>
    </div>
  );
}
