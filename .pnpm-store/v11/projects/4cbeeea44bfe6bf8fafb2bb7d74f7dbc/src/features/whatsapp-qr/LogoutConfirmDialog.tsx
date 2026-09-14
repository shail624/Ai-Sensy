import { Modal } from "@/components/ui";
import { apiErrorMessage } from "@/features/whatsapp-qr/api";

interface Props {
  identityLabel: string;
  pending: boolean;
  error: unknown;
  onConfirm: () => void;
  onClose: () => void;
}

/**
 * The one destructive action on this screen. Logout invalidates the WhatsApp credentials at the
 * provider — certification proved the account then requires a brand-new scan — so this is never
 * triggered by anything but an explicit, confirmed click.
 */
export function LogoutConfirmDialog({
  identityLabel,
  pending,
  error,
  onConfirm,
  onClose,
}: Props): JSX.Element {
  return (
    <Modal title="Log out of WhatsApp?" onClose={onClose}>
      <p className="text-sm text-text-secondary">
        This disconnects <span className="font-medium text-text-primary">{identityLabel}</span>.
        Messaging stops immediately, and reconnecting requires scanning a new QR code with the
        phone.
      </p>
      <p className="mt-2 text-sm text-text-secondary">This cannot be undone from here.</p>
      {error ? <p className="mt-3 text-sm text-danger">{apiErrorMessage(error)}</p> : null}
      <div className="mt-5 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          disabled={pending}
          className="rounded-control border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={pending}
          className="rounded-control bg-danger px-3 py-1.5 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Logging out…" : "Log out"}
        </button>
      </div>
    </Modal>
  );
}
