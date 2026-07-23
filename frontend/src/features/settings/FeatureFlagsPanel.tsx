import { useMemo, useState } from "react";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useFeatureFlags,
  useHasPermission,
  useUpdateFeatureFlag,
} from "@/features/settings/api";
import type { FeatureFlag } from "@/features/settings/types";
import { MAX_FLAG_DESCRIPTION } from "@/features/settings/types";
import { formatCount, formatDateTime } from "@/lib/format";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function FlagStateChip({ enabled }: { enabled: boolean }): JSX.Element {
  return (
    <span className={chip(enabled ? "border-success text-success" : "border-border text-text-disabled")}>
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}

/**
 * Feature flags (Doc 05 B11.11).
 *
 * Two facts shape this screen. Flags are **global** — the list endpoint reads platform-wide flags,
 * not per-organization ones, so every flag's scope is the whole deployment. And **nothing in the
 * platform reads them yet**: the table exists so modules can ship dark, but no code checks
 * `is_enabled`, so toggling one changes no behaviour today. Both are said on screen rather than
 * left for someone to discover after flipping a switch and seeing nothing happen.
 */
export function FeatureFlagsPanel(): JSX.Element {
  const canManage = useHasPermission("settings:manage");
  const flags = useFeatureFlags();
  const update = useUpdateFeatureFlag();

  const [editing, setEditing] = useState<string | null>(null);
  const [description, setDescription] = useState("");

  const rows = useMemo(
    () => [...(flags.data ?? [])].sort((a, b) => a.key.localeCompare(b.key)),
    [flags.data],
  );
  const enabled = rows.filter((flag) => flag.is_enabled).length;

  if (flags.isLoading) return <Spinner label="Loading feature flags…" />;

  if (flags.isError) {
    return <ErrorState message={apiErrorMessage(flags.error)} onRetry={() => void flags.refetch()} />;
  }

  function startEditing(flag: FeatureFlag): void {
    setEditing(flag.key);
    setDescription(flag.description ?? "");
  }

  return (
    <Section title="Feature flags">
      <p className="mb-3 text-sm text-text-secondary">
        {rows.length === 0
          ? "No flags are registered."
          : `${formatCount(rows.length)} flag${rows.length === 1 ? "" : "s"} · ${formatCount(enabled)} enabled`}
      </p>

      <p className="mb-3 rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-text-secondary">
        Flags are global to this deployment, not per-organization. No module reads them yet — the
        table exists so features can ship dark, so toggling a flag changes no behaviour today.
      </p>

      {update.error ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(update.error)} />
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState
          title="No feature flags"
          description="Flags are created on demand — none has been registered yet."
        />
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
              <tr>
                <th scope="col" className="px-3 py-2">Flag</th>
                <th scope="col" className="px-3 py-2">State</th>
                <th scope="col" className="hidden px-3 py-2 lg:table-cell">Targeting</th>
                <th scope="col" className="hidden px-3 py-2 xl:table-cell">Last updated</th>
                <th scope="col" className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((flag) => (
                <tr key={flag.key} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 align-top">
                    <p className="break-all font-mono text-xs text-text-primary">{flag.key}</p>
                    <p className="text-xs text-text-disabled">Global</p>

                    {editing === flag.key ? (
                      <div className="mt-2">
                        <label
                          htmlFor={`flag-description-${flag.key}`}
                          className="text-xs font-medium text-text-secondary"
                        >
                          Description
                        </label>
                        <textarea
                          id={`flag-description-${flag.key}`}
                          rows={2}
                          maxLength={MAX_FLAG_DESCRIPTION}
                          value={description}
                          onChange={(event) => setDescription(event.target.value)}
                          className={FIELD_CLASS}
                        />
                        <p className="mt-1 text-xs text-text-disabled">
                          {description.length}/{MAX_FLAG_DESCRIPTION}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => setEditing(null)}
                            disabled={update.isPending}
                            className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover disabled:opacity-50"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            disabled={update.isPending}
                            onClick={() =>
                              update.mutate(
                                { key: flag.key, body: { description: description.trim() || null } },
                                { onSuccess: () => setEditing(null) },
                              )
                            }
                            className="rounded-md bg-accent px-2 py-1 text-xs text-accent-fg disabled:opacity-50"
                          >
                            {update.isPending ? "Saving…" : "Save description"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-1 max-w-md text-sm text-text-secondary">
                        {flag.description ?? "No description."}
                      </p>
                    )}
                  </td>

                  <td className="px-3 py-2 align-top">
                    <FlagStateChip enabled={flag.is_enabled} />
                  </td>

                  <td className="hidden px-3 py-2 align-top lg:table-cell">
                    {flag.rollout && Object.keys(flag.rollout).length > 0 ? (
                      <pre className="max-w-xs overflow-x-auto rounded border border-border bg-surface-2 p-2 text-xs text-text-primary">
                        {JSON.stringify(flag.rollout, null, 2)}
                      </pre>
                    ) : (
                      <span className="text-xs text-text-disabled">All or nothing</span>
                    )}
                  </td>

                  <td className="hidden px-3 py-2 align-top text-xs text-text-secondary xl:table-cell">
                    {formatDateTime(flag.updated_at)}
                  </td>

                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap justify-end gap-1">
                      {canManage ? (
                        <>
                          <button
                            type="button"
                            disabled={update.isPending}
                            onClick={() =>
                              update.mutate({
                                key: flag.key,
                                body: { is_enabled: !flag.is_enabled },
                              })
                            }
                            className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50"
                          >
                            {flag.is_enabled ? "Disable" : "Enable"}
                          </button>
                          {editing !== flag.key ? (
                            <button
                              type="button"
                              onClick={() => startEditing(flag)}
                              className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover"
                            >
                              Describe
                            </button>
                          ) : null}
                        </>
                      ) : (
                        <span className="text-xs text-text-disabled">Read-only</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 text-xs text-text-disabled">
        Targeting rules are stored as free-form JSON and shown as received; there is no editor for
        them, because the platform defines no rollout schema to validate against.
      </p>
    </Section>
  );
}
