import { useState } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useConnectWaba, useUpdateWaba } from "@/features/channels/api";
import type { Waba } from "@/features/channels/types";
import { WABA_STATUS_LABELS, WABA_STATUSES } from "@/features/channels/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

interface Props {
  /** Present → edit that account (metadata, status, token rotation); absent → connect a new one. */
  waba?: Waba;
  onClose: () => void;
  onConnected?: (waba: Waba) => void;
}

interface Draft {
  waba_id: string;
  business_name: string;
  access_token: string;
  meta_business_id: string;
  currency: string;
  timezone: string;
  status: string;
  token_expires_at: string;
}

function draftFor(waba: Waba | undefined): Draft {
  return {
    waba_id: waba?.waba_id ?? "",
    business_name: waba?.business_name ?? "",
    access_token: "",
    meta_business_id: waba?.meta_business_id ?? "",
    currency: waba?.currency ?? "",
    timezone: waba?.timezone ?? "",
    status: waba?.status ?? "active",
    token_expires_at: waba?.token_expires_at ? waba.token_expires_at.slice(0, 16) : "",
  };
}

/**
 * Connect a WABA, or amend one (Doc 05 B11.5).
 *
 * The system-user token is **write-only** — it is encrypted before storage and no response carries
 * it — so an edit shows an empty token field that means "leave it alone", and filling it means
 * "rotate to this". There is nothing to pre-fill it with, and nothing that could read it back.
 *
 * Meta's WABA id is globally unique and set once; on an edit it is shown read-only, because
 * changing it would mean pointing this row at a different account rather than editing this one.
 */
export function WabaFormDialog({ waba, onClose, onConnected }: Props): JSX.Element {
  const editing = waba !== undefined;
  const [draft, setDraft] = useState<Draft>(() => draftFor(waba));
  const [showErrors, setShowErrors] = useState(false);

  const connect = useConnectWaba();
  const update = useUpdateWaba();
  const pending = connect.isPending || update.isPending;
  const error = connect.error ?? update.error;

  const problems: Partial<Record<keyof Draft, string>> = {};
  if (draft.business_name.trim() === "") problems.business_name = "Business name is required";
  if (!editing) {
    if (draft.waba_id.trim() === "") problems.waba_id = "Meta's WABA id is required";
    if (draft.access_token.trim() === "") problems.access_token = "A system-user token is required";
  }
  if (draft.currency && draft.currency.trim().length !== 3) {
    problems.currency = "Use a 3-letter code such as INR";
  }
  const visible = showErrors ? problems : {};

  function set<K extends keyof Draft>(key: K, value: Draft[K]): void {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function submit(): void {
    setShowErrors(true);
    if (Object.keys(problems).length > 0) return;

    const expires = draft.token_expires_at
      ? new Date(draft.token_expires_at).toISOString()
      : null;

    if (editing) {
      update.mutate(
        {
          wabaId: waba.id,
          body: {
            business_name: draft.business_name.trim(),
            // An empty token field means "keep the stored one" — sending null would be a change.
            ...(draft.access_token.trim() ? { access_token: draft.access_token.trim() } : {}),
            currency: draft.currency.trim() || null,
            timezone: draft.timezone.trim() || null,
            status: draft.status,
            token_expires_at: expires,
            row_version: waba.row_version,
          },
        },
        { onSuccess: onClose },
      );
      return;
    }

    connect.mutate(
      {
        waba_id: draft.waba_id.trim(),
        business_name: draft.business_name.trim(),
        access_token: draft.access_token.trim(),
        meta_business_id: draft.meta_business_id.trim() || null,
        currency: draft.currency.trim() || null,
        timezone: draft.timezone.trim() || null,
        token_expires_at: expires,
      },
      {
        onSuccess: (created) => {
          onConnected?.(created);
          onClose();
        },
      },
    );
  }

  return (
    <Modal
      title={editing ? `Edit ${waba.business_name}` : "Connect a WhatsApp Business Account"}
      onClose={onClose}
    >
      <div className="space-y-3">
        <div>
          <label htmlFor="waba-id" className={LABEL_CLASS}>
            WABA id (from Meta)
          </label>
          <input
            id="waba-id"
            value={draft.waba_id}
            disabled={editing}
            onChange={(event) => set("waba_id", event.target.value)}
            placeholder="102938475610293"
            className={`${FIELD_CLASS} font-mono disabled:opacity-60`}
          />
          {editing ? (
            <p className="mt-1 text-xs text-text-disabled">
              Set once — it identifies the account at Meta.
            </p>
          ) : null}
          {visible.waba_id ? <p className="text-xs text-danger">{visible.waba_id}</p> : null}
        </div>

        <div>
          <label htmlFor="waba-name" className={LABEL_CLASS}>
            Business name
          </label>
          <input
            id="waba-name"
            value={draft.business_name}
            onChange={(event) => set("business_name", event.target.value)}
            className={FIELD_CLASS}
          />
          {visible.business_name ? (
            <p className="text-xs text-danger">{visible.business_name}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="waba-token" className={LABEL_CLASS}>
            {editing ? "Rotate token (optional)" : "System-user token"}
          </label>
          <input
            id="waba-token"
            type="password"
            autoComplete="off"
            value={draft.access_token}
            onChange={(event) => set("access_token", event.target.value)}
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            {editing
              ? "Leave empty to keep the stored token. The token is encrypted and never shown again, so there is nothing to pre-fill here."
              : "Encrypted before it is stored and never returned by the API."}
          </p>
          {visible.access_token ? (
            <p className="text-xs text-danger">{visible.access_token}</p>
          ) : null}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="waba-token-expiry" className={LABEL_CLASS}>
              Token expires (optional)
            </label>
            <input
              id="waba-token-expiry"
              type="datetime-local"
              value={draft.token_expires_at}
              onChange={(event) => set("token_expires_at", event.target.value)}
              className={FIELD_CLASS}
            />
            <p className="mt-1 text-xs text-text-disabled">
              Recording it is what lets the platform warn you before sends start failing.
            </p>
          </div>

          {editing ? (
            <div>
              <label htmlFor="waba-status" className={LABEL_CLASS}>
                Status
              </label>
              <select
                id="waba-status"
                value={draft.status}
                onChange={(event) => set("status", event.target.value)}
                className={FIELD_CLASS}
              >
                {WABA_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {WABA_STATUS_LABELS[status]}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label htmlFor="waba-business-id" className={LABEL_CLASS}>
                Meta business id (optional)
              </label>
              <input
                id="waba-business-id"
                value={draft.meta_business_id}
                onChange={(event) => set("meta_business_id", event.target.value)}
                className={`${FIELD_CLASS} font-mono`}
              />
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="waba-currency" className={LABEL_CLASS}>
              Currency (optional)
            </label>
            <input
              id="waba-currency"
              value={draft.currency}
              onChange={(event) => set("currency", event.target.value.toUpperCase())}
              placeholder="INR"
              maxLength={3}
              className={`${FIELD_CLASS} font-mono`}
            />
            {visible.currency ? <p className="text-xs text-danger">{visible.currency}</p> : null}
          </div>
          <div>
            <label htmlFor="waba-timezone" className={LABEL_CLASS}>
              Timezone (optional)
            </label>
            <input
              id="waba-timezone"
              value={draft.timezone}
              onChange={(event) => set("timezone", event.target.value)}
              placeholder="Asia/Kolkata"
              className={FIELD_CLASS}
            />
          </div>
        </div>

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
            {pending ? "Saving…" : editing ? "Save changes" : "Connect account"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
