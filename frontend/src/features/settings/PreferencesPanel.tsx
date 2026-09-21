import { useMemo } from "react";

import { ErrorState, Section, Spinner } from "@/components/ui";
import { NotificationSettingsPanel } from "@/features/notifications/NotificationSettingsPanel";
import {
  apiErrorMessage,
  usePreferences,
  useUpdatePreferences,
} from "@/features/settings/api";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";

/**
 * The signed-in user's own preferences.
 *
 * Gated on `auth:self`, which every account holds — this is the one part of Settings that does not
 * need `settings:read`, because it is about you rather than the platform.
 *
 * Like the other two stores it is schemaless: `dict[str, Any]`, nothing seeded, no catalog. The
 * theme and sidebar state this app actually uses live in browser storage, not here, so these keys
 * are whatever has been written to them.
 */
export function PreferencesPanel(): JSX.Element {
  const preferences = usePreferences();
  const update = useUpdatePreferences();

  const entries: KeyValueEntry[] = useMemo(
    () =>
      Object.entries(preferences.data ?? {}).map(([key, value]) => ({
        key,
        value,
        editable: true,
      })),
    [preferences.data],
  );

  if (preferences.isLoading) return <Spinner label="Loading your preferences…" />;

  if (preferences.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(preferences.error)}
        onRetry={() => void preferences.refetch()}
      />
    );
  }

  return (
    <Section
      title="Notification Preferences"
      description="Choose which operational updates appear in your personal notification centre."
    >
      <div className="overflow-hidden rounded-xl border border-border">
        <div className="border-b border-border bg-surface px-4 py-3 sm:px-5">
          <h3 className="text-sm font-semibold text-text-primary">Notification categories</h3>
          <p className="mt-1 text-xs text-text-secondary">
            Changes apply only to your account and save as soon as you select them.
          </p>
        </div>
        <NotificationSettingsPanel open />
      </div>

      <div className="mt-6 border-t border-border pt-5">
        <h3 className="mb-1 text-sm font-semibold text-text-primary">Advanced preferences</h3>
        <p className="mb-4 text-xs text-text-secondary">
          Personal server-synced settings used by internal workflows.
        </p>
        <KeyValueEditor
          entries={entries}
          onSave={(values) => update.mutate(values)}
          canEdit
          pending={update.isPending}
          error={update.error}
          allowAdd
          emptyTitle="No advanced preferences stored"
          emptyDescription="Nothing else has been saved against your account yet."
          note="Your own settings are stored server-side and visible only to you. The theme and sidebar state this app uses are kept in this browser instead, so they do not appear here."
        />
      </div>
    </Section>
  );
}
