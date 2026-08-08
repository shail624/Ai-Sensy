import type { components } from "@/lib/api/schema";

/** The server's own provider-neutral status shape — never redeclared by hand (Doc 07 §5.2). */
export type WhatsAppQrStatus = components["schemas"]["WhatsAppQrStatus"];

/** `session_state` values the server can report (`app.channels.session.SessionState`). */
export const SESSION_STATE = {
  REGISTERED: "registered",
  INITIALIZING: "initializing",
  WAITING_FOR_PAIRING: "waiting_for_pairing",
  ACTIVE: "active",
  DEGRADED: "degraded",
  RECONNECTING: "reconnecting",
  PAUSED: "paused",
  EXPIRED: "expired",
  TERMINATED: "terminated",
} as const;

/** `pairing_state` values the server can report (`app.channels.runtime.PairingState`). */
export const PAIRING_STATE = {
  UNPAIRED: "unpaired",
  PAIRING_REQUESTED: "pairing_requested",
  PAIRING_AVAILABLE: "pairing_available",
  PAIRING_EXPIRED: "pairing_expired",
  PAIRING_CANCELLED: "pairing_cancelled",
  PAIRED: "paired",
} as const;
