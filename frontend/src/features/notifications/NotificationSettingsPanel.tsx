import { useEffect, useState } from "react";

import { Button, ErrorState, Skeleton } from "@/components/ui";
import {
  useNotificationSettings,
  useUpdateNotificationSettings,
} from "@/features/notifications/api";
import {
  NOTIFICATION_TYPES,
  type MutedTypes,
  type NotificationTypeName,
} from "@/features/notifications/types";
import { apiErrorMessage } from "@/lib/api/errors";

interface NotificationSettingsPanelProps {
  open: boolean;
}

/**
 * Which categories this operator wants in their own list.
 *
 * Phrased as "show me", not "mute": a checked box is a category you see, which is the way the
 * question is actually asked. The stored value is the complement, because the server's default —
 * an absent setting — has to mean "show everything".
 */
export function NotificationSettingsPanel({ open }: NotificationSettingsPanelProps) {
  const settings = useNotificationSettings(open);
  const save = useUpdateNotificationSettings();
  const [muted, setMuted] = useState<MutedTypes>([]);

  const serverMuted = settings.data?.muted_types;
  useEffect(() => {
    // Adopt the server's answer, except while a save of our own is still in flight: the list would
    // otherwise snap back to the pre-toggle value for as long as the round trip takes.
    if (serverMuted && !save.isPending) setMuted(serverMuted);
  }, [serverMuted, save.isPending]);

  function toggle(name: NotificationTypeName): void {
    const next = muted.includes(name)
      ? muted.filter((item) => item !== name)
      : [...muted, name].sort();
    setMuted(next);
    save.mutate(next);
  }

  if (!open) return null;

  return (
    <section
      aria-label="Notification settings"
      className="border-b border-border bg-surface-muted px-4 py-3 sm:px-5"
    >
      <p className="text-xs text-text-secondary">
        Hidden categories are still recorded, and your team lead still sees them. Turning one back
        on brings anything you missed back unread.
      </p>

      {settings.isPending ? (
        <div className="mt-3 space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : settings.isError ? (
        <div className="mt-3">
          <ErrorState
            message={apiErrorMessage(settings.error)}
            onRetry={() => void settings.refetch()}
          />
        </div>
      ) : (
        <ul className="mt-3 grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
          {NOTIFICATION_TYPES.map(([name, label]) => {
            const shown = !muted.includes(name);
            return (
              <li key={name}>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-text-primary">
                  <input
                    type="checkbox"
                    checked={shown}
                    disabled={save.isPending}
                    onChange={() => toggle(name)}
                    className="h-4 w-4 rounded border-border accent-accent"
                  />
                  <span>{label}</span>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      {save.isError ? (
        <div role="alert" className="mt-3 text-xs text-danger">
          {apiErrorMessage(save.error)}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="ml-2 px-2 text-xs"
            onClick={() => save.mutate(muted)}
          >
            Try again
          </Button>
        </div>
      ) : null}
    </section>
  );
}
