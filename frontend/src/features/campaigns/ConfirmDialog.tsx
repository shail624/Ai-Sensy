import { Modal } from "@/components/ui";
import { apiErrorMessage } from "@/features/campaigns/api";

interface Props {
  title: string;
  /** What the action will do, in the operator's terms — including anything it cannot undo. */
  body: string;
  confirmLabel: string;
  destructive?: boolean;
  pending: boolean;
  error: unknown;
  onConfirm: () => void;
  onClose: () => void;
}

/**
 * Confirmation gate for the campaign actions that reach real customers or destroy work — dispatch,
 * cancel and delete. The mutation's own error is rendered in place rather than closing the dialog,
 * so a rejected transition (the server's 409, Doc 04 §17) is read where the decision was made.
 */
export function ConfirmDialog({
  title,
  body,
  confirmLabel,
  destructive = false,
  pending,
  error,
  onConfirm,
  onClose,
}: Props): JSX.Element {
  return (
    <Modal title={title} onClose={onClose}>
      <p className="text-sm text-text-secondary">{body}</p>
      {error ? <p className="mt-3 text-sm text-danger">{apiErrorMessage(error)}</p> : null}
      <div className="mt-4 flex justify-end gap-2">
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
          onClick={onConfirm}
          disabled={pending}
          className={`rounded-md px-3 py-1 text-sm disabled:opacity-50 ${
            destructive
              ? "bg-danger text-accent-fg"
              : "bg-accent text-accent-fg"
          }`}
        >
          {pending ? "Working…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
