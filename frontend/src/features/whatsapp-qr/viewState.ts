import { PAIRING_STATE, SESSION_STATE, type WhatsAppQrStatus } from "@/features/whatsapp-qr/types";

export type WhatsAppQrViewState =
  | "not-configured"
  | "ready-to-connect"
  | "ready-to-pair"
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

  // QR-09-D8: a current provider outage is a live action boundary, so it outranks every durable
  // lifecycle value below. The backend now emits this reason only for an observed transport
  // outage; checking it here as well prevents a stale/internally inconsistent `qr_available`
  // response from mounting the QR flow. A reachable-but-missing provider session stays distinct.
  if (
    status.reconnect_blocked_reason === "provider_unavailable" &&
    !status.provider_session_missing
  ) {
    return "provider-unavailable";
  }

  if (status.connected) return "connected";
  if (status.requires_reauthentication) return "reauth-required";

  // The provider is reachable and holds no session for this connection (QR-09-D2). Nothing is
  // starting and nothing will arrive by waiting, so this must sit above every "in progress"
  // branch below — otherwise a durable session record with no provider session behind it renders
  // as "Starting…", which is exactly the false progress the operator would sit and wait on.
  //
  // A connection that had reached PAIRED is already handled above as `reauth-required` (the server
  // sets `requires_reauthentication` for that case, because credentials genuinely were lost).
  // Everything else has nothing to re-authenticate, and the durable application session is what
  // separates the two honest operator actions:
  //   * no durable session -> `connect()` is the action that creates one.
  //   * durable session     -> `connect()` is idempotent and provably cannot create provider state,
  //                            so offering it again is a dead end (QR-09-D6): status polling kept
  //                            replacing "Begin pairing" with a "Connect WhatsApp" that did
  //                            nothing, leaving `/session/pair` operationally unreachable. Pairing
  //                            is the only action that can move this forward.
  // This branch is only reached on a live SESSION_MISSING observation, which the backend emits
  // exclusively of PROVIDER_UNAVAILABLE — so reaching here already means the provider answered,
  // and a real outage is caught by the check above (QR-09-D8) before any of this runs.
  if (status.provider_session_missing) {
    return status.session_public_id ? "ready-to-pair" : "ready-to-connect";
  }

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
