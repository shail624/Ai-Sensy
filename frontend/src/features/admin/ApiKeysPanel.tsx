import { useMemo, useState } from "react";

import { EmptyState, ErrorState, Modal, Spinner } from "@/components/ui";
import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { ApiKeyStateChip, PermissionChip } from "@/features/admin/AdminBadges";
import {
  apiErrorMessage,
  useApiKeys,
  useCreateApiKey,
  useHasPermission,
  usePermissions,
  useRevokeApiKey,
  useRotateApiKey,
} from "@/features/admin/api";
import { ApiKeySecretDialog } from "@/features/admin/ApiKeySecretDialog";
import type { ApiKey, ApiKeyCreated } from "@/features/admin/types";
import { apiKeyState } from "@/features/admin/types";
import { formatAge, formatDateTime, UNKNOWN } from "@/lib/format";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";
const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Issued {
  created: ApiKeyCreated;
  rotationLeftOldKeyLive?: boolean;
}

/**
 * API key administration (Doc 05 B11.4).
 *
 * Everything on this screen is shaped by one property of the backend: the secret exists in the
 * response and nowhere else. So creation hands straight to a copy-once dialog, rotation issues the
 * replacement *before* revoking the original — no window where neither key works — and the list
 * shows only the prefix, because that is genuinely all there is to show.
 */
export function ApiKeysPanel(): JSX.Element {
  const [creating, setCreating] = useState(false);
  const [rotating, setRotating] = useState<ApiKey | null>(null);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const [issued, setIssued] = useState<Issued | null>(null);

  // Reads and writes share one permission here: `apikeys:manage` guards the whole resource.
  const canManage = useHasPermission("apikeys:manage");
  const keys = useApiKeys();
  const revoke = useRevokeApiKey();

  const rows = useMemo(
    () =>
      [...(keys.data ?? [])].sort(
        (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
      ),
    [keys.data],
  );

  if (keys.isLoading) return <Spinner label="Loading API keys…" />;

  if (keys.isError) {
    return <ErrorState message={apiErrorMessage(keys.error)} onRetry={() => void keys.refetch()} />;
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-text-secondary">
          Keys authenticate integrations. Each secret is shown once, at creation.
        </p>
        {canManage ? (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            New API key
          </button>
        ) : null}
      </div>

      {revoke.error && !revoking ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(revoke.error)} />
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState
          title="No API keys"
          description={
            canManage
              ? "Create a key to let an integration call this platform's API."
              : "No API keys have been created."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
              <tr>
                <th scope="col" className="px-3 py-2">Key</th>
                <th scope="col" className="px-3 py-2">State</th>
                <th scope="col" className="hidden px-3 py-2 lg:table-cell">Scopes</th>
                <th scope="col" className="hidden px-3 py-2 md:table-cell">Expires</th>
                <th scope="col" className="hidden px-3 py-2 xl:table-cell">Last used</th>
                <th scope="col" className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((key) => {
                const state = apiKeyState(key);
                return (
                  <tr key={key.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-3 py-2">
                      <p className="font-medium text-text-primary">{key.name}</p>
                      <p className="font-mono text-xs text-text-disabled">{key.key_prefix}…</p>
                    </td>
                    <td className="px-3 py-2">
                      <ApiKeyStateChip state={state} />
                    </td>
                    <td className="hidden px-3 py-2 lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {key.scopes.length === 0 ? (
                          <span className="text-xs text-text-disabled">No scopes</span>
                        ) : (
                          key.scopes.map((scope) => <PermissionChip key={scope} code={scope} />)
                        )}
                      </div>
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                      {key.expires_at ? (
                        <>
                          {formatDateTime(key.expires_at)}
                          {state === "expired" ? (
                            <span className="block text-xs text-warning">expired</span>
                          ) : null}
                        </>
                      ) : (
                        <span className="text-text-disabled">Never</span>
                      )}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {key.last_used_at ? formatAge(key.last_used_at) : UNKNOWN}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap justify-end gap-1">
                        {canManage && state !== "revoked" ? (
                          <>
                            <button
                              type="button"
                              className={ACTION_CLASS}
                              onClick={() => setRotating(key)}
                            >
                              Rotate
                            </button>
                            <button
                              type="button"
                              className={`${ACTION_CLASS} text-danger`}
                              onClick={() => setRevoking(key)}
                            >
                              Revoke
                            </button>
                          </>
                        ) : (
                          <span className="text-xs text-text-disabled">
                            {state === "revoked" ? "Revoked" : ""}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {creating ? (
        <ApiKeyDialog
          onClose={() => setCreating(false)}
          onIssued={(created) => {
            setCreating(false);
            setIssued({ created });
          }}
        />
      ) : null}

      {rotating ? (
        <ApiKeyDialog
          rotating={rotating}
          onClose={() => setRotating(null)}
          onIssued={(created, leftOldKeyLive) => {
            setRotating(null);
            setIssued({ created, rotationLeftOldKeyLive: leftOldKeyLive });
          }}
        />
      ) : null}

      {issued ? (
        <ApiKeySecretDialog
          created={issued.created}
          rotationLeftOldKeyLive={issued.rotationLeftOldKeyLive}
          onClose={() => setIssued(null)}
        />
      ) : null}

      {revoking ? (
        <ConfirmDialog
          title={`Revoke "${revoking.name}"?`}
          body="Any integration using this key stops working immediately. This cannot be undone — issue a new key instead."
          confirmLabel="Revoke key"
          destructive
          pending={revoke.isPending}
          error={revoke.error}
          onClose={() => setRevoking(null)}
          onConfirm={() =>
            revoke.mutate(revoking.id, { onSuccess: () => setRevoking(null) })
          }
        />
      ) : null}
    </>
  );
}

interface DialogProps {
  /** Present → issue a replacement for this key and revoke it; absent → create a new key. */
  rotating?: ApiKey;
  onClose: () => void;
  onIssued: (created: ApiKeyCreated, rotationLeftOldKeyLive?: boolean) => void;
}

/**
 * Name, scopes and expiry for a new key — used for both creation and rotation, because a rotation
 * *is* a creation plus a revoke, and the operator makes the same decisions either way.
 */
function ApiKeyDialog({ rotating, onClose, onIssued }: DialogProps): JSX.Element {
  const [name, setName] = useState(rotating ? rotating.name : "");
  const [scopes, setScopes] = useState<string[]>(rotating ? [...rotating.scopes] : []);
  const [expiresAt, setExpiresAt] = useState("");
  const [showErrors, setShowErrors] = useState(false);

  const permissions = usePermissions();
  const create = useCreateApiKey();
  const rotate = useRotateApiKey();

  const pending = create.isPending || rotate.isPending;
  const error = create.error ?? rotate.error;
  const problem = name.trim() === "" ? "Name is required" : null;

  function toggleScope(code: string): void {
    setScopes((current) =>
      current.includes(code) ? current.filter((entry) => entry !== code) : [...current, code],
    );
  }

  function submit(): void {
    setShowErrors(true);
    if (problem) return;

    const body = {
      name: name.trim(),
      scopes,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    };

    if (rotating) {
      rotate.mutate(
        { previous: rotating, body },
        { onSuccess: (result) => onIssued(result.created, !result.revoked) },
      );
      return;
    }
    create.mutate(body, { onSuccess: (created) => onIssued(created) });
  }

  return (
    <Modal title={rotating ? `Rotate "${rotating.name}"` : "New API key"} onClose={onClose}>
      <div className="space-y-3">
        {rotating ? (
          <p className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-text-secondary">
            A replacement is issued first, then the current key is revoked — so there is no moment
            when neither works. Update the integration with the new secret promptly.
          </p>
        ) : null}

        <div>
          <label htmlFor="key-name" className={LABEL_CLASS}>
            Name
          </label>
          <input
            id="key-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="billing-sync"
            className={FIELD_CLASS}
          />
          {showErrors && problem ? <p className="text-xs text-danger">{problem}</p> : null}
        </div>

        <div>
          <label htmlFor="key-expires" className={LABEL_CLASS}>
            Expires (optional)
          </label>
          <input
            id="key-expires"
            type="datetime-local"
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.target.value)}
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            Leave empty for a key that never expires. An expiry is the cheapest way to bound the
            damage of a leaked secret.
          </p>
        </div>

        <fieldset>
          <legend className={LABEL_CLASS}>Scopes</legend>
          <p className="mt-1 text-xs text-text-disabled">
            Grant only what the integration needs. No scopes means the key carries none.
          </p>
          <div className="mt-2 max-h-48 overflow-y-auto rounded-md border border-border p-2">
            <div className="flex flex-wrap gap-1">
              {(permissions.data ?? []).map((permission) => {
                const selected = scopes.includes(permission.code);
                return (
                  <button
                    key={permission.code}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleScope(permission.code)}
                    title={permission.description ?? undefined}
                    className={`rounded-full border px-2 py-0.5 font-mono text-xs ${
                      selected
                        ? "border-accent text-accent"
                        : "border-border text-text-secondary hover:bg-hover"
                    }`}
                  >
                    {permission.code}
                  </button>
                );
              })}
            </div>
          </div>
        </fieldset>

        {error ? <p className="text-sm text-danger">{apiErrorMessage(error)}</p> : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {pending ? "Working…" : rotating ? "Rotate key" : "Create key"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
