import { useMemo } from "react";

import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useSettings,
  useUpdateSettings,
} from "@/features/settings/api";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";
import type { Setting } from "@/features/settings/types";
import {
  isEditableSetting,
  SCOPE_EXPLANATIONS,
  SCOPE_LABELS,
  SCOPE_ORGANIZATION,
  SCOPE_SYSTEM,
} from "@/features/settings/types";
import { formatCount } from "@/lib/format";

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

/**
 * Application settings (Doc 05 B11.11).
 *
 * The settings store is a **schemaless key/value table with nothing seeded into it** — migration
 * `0003` states plainly that settings are created on demand, and no code seeds any. There is
 * therefore no catalog of known keys to build a form from, and no backend concept of "general
 * settings", "messaging defaults" or "retention settings": those are categories the platform does
 * not define.
 *
 * So this renders the store as it is — the keys that exist, grouped by scope — and lets an
 * operator add one. System-scoped rows are read-only, because `PUT /settings` upserts into the
 * organization scope unconditionally: writing a system key would not change it, it would create a
 * confusing second row with the same name.
 */
export function ApplicationPanel(): JSX.Element {
  const canManage = useHasPermission("settings:manage");
  const settings = useSettings();
  const update = useUpdateSettings();

  const all = useMemo(() => settings.data ?? [], [settings.data]);

  const orgEntries = useMemo(
    () =>
      all
        .filter((setting) => setting.scope === SCOPE_ORGANIZATION)
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
      <ErrorState
        message={apiErrorMessage(settings.error)}
        onRetry={() => void settings.refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <Section title="Organization settings">
        <KeyValueEditor
          entries={orgEntries}
          onSave={(values) => update.mutate(values)}
          canEdit={canManage}
          pending={update.isPending}
          error={update.error}
          allowAdd
          emptyTitle="No organization settings yet"
          emptyDescription="The settings store ships empty — keys are created the first time they are written."
          note="Configuration for this organization. The store is schemaless: a key exists once something writes it, and its type is whatever was stored."
        />
      </Section>

      <Section title="System settings">
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
            note="Read-only. The update endpoint writes to the organization scope only, so these cannot be changed here — they are set on the server."
          />
        )}
      </Section>

      <Section title="System information">
        <dl>
          <DefinitionRow label="Settings stored">{formatCount(all.length)}</DefinitionRow>
          <DefinitionRow label="Organization-scoped">
            {formatCount(orgEntries.length)}
          </DefinitionRow>
          <DefinitionRow label="System-scoped">{formatCount(systemEntries.length)}</DefinitionRow>
          <DefinitionRow label="Secret values">{formatCount(secrets)}</DefinitionRow>
        </dl>
        <p className="mt-3 text-xs text-text-disabled">
          Secret settings are stored but never returned — the API sends `null` in place of the
          value, so nothing here can display or change one. Retention, messaging defaults and
          similar policies are not modelled as settings: where the platform enforces them, it does
          so in code.
        </p>
      </Section>
    </div>
  );
}
