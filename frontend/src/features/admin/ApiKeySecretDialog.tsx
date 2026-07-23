import { useState } from "react";

import { Modal } from "@/components/ui";
import type { ApiKeyCreated } from "@/features/admin/types";
import { formatDateTime } from "@/lib/format";

interface Props {
  created: ApiKeyCreated;
  /** Set when this key replaced another and the old one could not be revoked. */
  rotationLeftOldKeyLive?: boolean;
  onClose: () => void;
}

/**
 * The one and only time the secret is visible.
 *
 * The server stores a hash and a prefix — nothing can retrieve this value again — so the dialog is
 * built around that fact: the secret is shown in full, copying is one click, and closing requires
 * confirming it has been stored. Anything softer invites an operator to close it and lose the key.
 */
export function ApiKeySecretDialog({
  created,
  rotationLeftOldKeyLive,
  onClose,
}: Props): JSX.Element {
  const [copied, setCopied] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard?.writeText(created.secret);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be refused (insecure context, denied permission). The secret is on
      // screen and selectable, so this fails quietly rather than raising an alarm.
      setCopied(false);
    }
  }

  return (
    <Modal title="Copy this key now" onClose={onClose}>
      <div className="space-y-3">
        <p className="rounded-md border border-warning px-3 py-2 text-sm text-warning">
          This is the only time the secret is shown. Only a hash is stored — if it is lost, the key
          must be rotated rather than recovered.
        </p>

        {rotationLeftOldKeyLive ? (
          <p role="alert" className="rounded-md border border-danger px-3 py-2 text-sm text-danger">
            The replacement was created, but the previous key could not be revoked. Two keys are
            live — revoke the old one from the list once the new one is in place.
          </p>
        ) : null}

        <div>
          <p className="text-xs font-medium text-text-secondary">Secret</p>
          <div className="mt-1 flex items-start gap-2">
            <code className="min-w-0 flex-1 break-all rounded-md border border-border bg-surface-2 px-3 py-2 font-mono text-xs text-text-primary">
              {created.secret}
            </code>
            <button
              type="button"
              onClick={() => void copy()}
              className="shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>

        <dl className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
          <div className="flex justify-between gap-2 py-0.5">
            <dt className="text-text-secondary">Name</dt>
            <dd className="text-text-primary">{created.name}</dd>
          </div>
          <div className="flex justify-between gap-2 py-0.5">
            <dt className="text-text-secondary">Prefix</dt>
            <dd className="font-mono text-text-primary">{created.key_prefix}</dd>
          </div>
          <div className="flex justify-between gap-2 py-0.5">
            <dt className="text-text-secondary">Expires</dt>
            <dd className="text-text-primary">
              {created.expires_at ? formatDateTime(created.expires_at) : "Never"}
            </dd>
          </div>
        </dl>

        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
            className="mt-1"
          />
          I have stored this secret somewhere safe.
        </label>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={!acknowledged}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
}
