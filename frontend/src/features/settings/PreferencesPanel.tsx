import { useMemo } from "react";

import { ErrorState, Section, Spinner } from "@/components/ui";
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
    <Section title="My preferences">
      <KeyValueEditor
        entries={entries}
        onSave={(values) => update.mutate(values)}
        canEdit
        pending={update.isPending}
        error={update.error}
        allowAdd
        emptyTitle="No preferences stored"
        emptyDescription="Nothing has been saved against your account yet."
        note="Your own settings, stored server-side and visible only to you. The theme and sidebar state this app uses are kept in this browser instead, so they do not appear here."
      />
    </Section>
  );
}
