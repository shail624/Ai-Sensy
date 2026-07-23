import { useState } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useUpdateNumber } from "@/features/channels/api";
import type { PhoneNumber } from "@/features/channels/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

/** The server's own bounds on `mps_limit` (`ge=1, le=1000`). */
const MIN_MPS = 1;
const MAX_MPS = 1000;

interface Props {
  number: PhoneNumber;
  onClose: () => void;
}

/**
 * Edit the operator-owned fields of a phone number (Doc 04 §13.3).
 *
 * Only three things are settable here, and the omissions are the design: quality rating, messaging
 * tier and throughput are **Meta-owned facts** that arrive via sync, so letting them be typed would
 * create a value the next sync silently undoes. The dialog says so rather than leaving their
 * absence to be discovered.
 */
export function NumberEditDialog({ number, onClose }: Props): JSX.Element {
  const [verifiedName, setVerifiedName] = useState(number.verified_name ?? "");
  const [mpsLimit, setMpsLimit] = useState(String(number.mps_limit));
  const [isDefault, setIsDefault] = useState(number.is_default);
  const [showErrors, setShowErrors] = useState(false);

  const update = useUpdateNumber();

  const parsed = Number.parseInt(mpsLimit, 10);
  const problem =
    Number.isNaN(parsed) || parsed < MIN_MPS || parsed > MAX_MPS
      ? `Enter a pacing limit between ${MIN_MPS} and ${MAX_MPS}`
      : verifiedName.length > 160
        ? "Display name is too long"
        : null;

  function submit(): void {
    setShowErrors(true);
    if (problem) return;
    update.mutate(
      {
        numberId: number.id,
        body: {
          verified_name: verifiedName.trim() || null,
          mps_limit: parsed,
          is_default: isDefault,
          row_version: number.row_version,
        },
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title={`Edit ${number.display_number}`} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="number-name" className={LABEL_CLASS}>
            Display name
          </label>
          <input
            id="number-name"
            value={verifiedName}
            onChange={(event) => setVerifiedName(event.target.value)}
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            What this number is called inside the platform. The next sync from Meta may overwrite it
            with the name Meta has verified.
          </p>
        </div>

        <div>
          <label htmlFor="number-mps" className={LABEL_CLASS}>
            Send pacing (messages per second)
          </label>
          <input
            id="number-mps"
            type="number"
            min={MIN_MPS}
            max={MAX_MPS}
            value={mpsLimit}
            onChange={(event) => setMpsLimit(event.target.value)}
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            The rate gate paces campaign sends to this figure. Lower it to protect a number whose
            quality has dipped; it never opens beyond what Meta allows.
          </p>
        </div>

        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(event) => setIsDefault(event.target.checked)}
            className="mt-1"
          />
          Use as the default number when a send names none.
        </label>

        <p className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-text-secondary">
          Quality rating, messaging tier and throughput are set by Meta and cannot be edited here —
          they update when the number is refreshed.
        </p>

        {showErrors && problem ? <p className="text-sm text-danger">{problem}</p> : null}
        {update.error ? (
          <p className="text-sm text-danger">{apiErrorMessage(update.error)}</p>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={update.isPending}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={update.isPending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {update.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
