import { PAIRING_STATE, SESSION_STATE, type WhatsAppQrStatus } from "@/features/whatsapp-qr/types";

export type WhatsAppQrViewState =
  | "not-configured"
  | "ready-to-connect"
  | "creating-session"
  | "qr-available"
  | "qr-expired"
  | "connecting"
  | "connected"
  | "reconnect-available"
  | "provider-unavailable"
  | "reauth-required";

/**
 * One pure mapping from the server's provider-neutral status to what the screen shows.
 *
 * Ordered by how definite the signal is: connected and re-auth-required are unambiguous outcomes
 * and are checked first: whichever the server reports takes priority over merely-transient
 * signals like the raw `provider_status` echo (which is informational only — see the backend
 * schema — and is used here only to distinguish "still trying" from "gave up", never to overrule
 * `pairing_state`/`session_state`, the values it is provider-neutral).
 */
export function deriveViewState(status: WhatsAppQrStatus | undefined): WhatsAppQrViewState {
  if (!status || !status.configured) return "not-configured";
  if (status.connected) return "connected";
  if (status.requires_reauthentication) return "reauth-required";

  // The provider is reachable and holds no session for this connection (QR-09-D2). Nothing is
  // starting and nothing will arrive by waiting, so this must sit above every "in progress"
  // branch below — otherwise a durable session record with no provider session behind it renders
  // as "Starting…", which is exactly the false progress the operator would sit and wait on.
  //
  // A connection that had reached PAIRED is already handled above as `reauth-required` (the server
  // sets `requires_reauthentication` for that case, because credentials genuinely were lost).
  // Everything else has nothing to re-authenticate: it needs the ordinary connect-and-scan action.
  if (status.provider_session_missing) return "ready-to-connect";

  if (!status.session_public_id) return "ready-to-connect";

  if (status.qr_available) return "qr-available";

  // A QR was requested but the provider never confirmed a scan before it lapsed: certification
  // observed this becomes provider status FAILED while durable pairing_state is still
  // "pairing_available" (nothing safe to infer overwrites it — see the backend service).
  if (
    status.pairing_state === PAIRING_STATE.PAIRING_AVAILABLE &&
    status.provider_status === "FAILED"
  ) {
    return "qr-expired";
  }

  // STARTING alone is genuinely ambiguous (QR-02/QR-06): it means either a session created for
  // the first time, or an already-paired one resuming. Durable `pairing_state` disambiguates —
  // only a session that has ever reached PAIRED is "connecting"; anything before that is still
  // "creating-session", the same distinction the backend's reconnect-safety logic makes.
  if (status.provider_status === "STARTING") {
    return status.pairing_state === PAIRING_STATE.PAIRED ? "connecting" : "creating-session";
  }

  if (status.can_reconnect) return "reconnect-available";

  if (
    status.session_state === SESSION_STATE.REGISTERED ||
    status.session_state === SESSION_STATE.INITIALIZING ||
    status.pairing_state === PAIRING_STATE.PAIRING_REQUESTED
  ) {
    return "creating-session";
  }

  return "provider-unavailable";
}
