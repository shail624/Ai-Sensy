import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Waba = components["schemas"]["WabaResponse"];
export type WabaList = components["schemas"]["WabaListResponse"];
export type WabaCreateRequest = components["schemas"]["WabaCreateRequest"];
export type WabaUpdateRequest = components["schemas"]["WabaUpdateRequest"];

export type PhoneNumber = components["schemas"]["PhoneNumberResponse"];
export type PhoneNumberList = components["schemas"]["PhoneNumbersListResponse"];
export type PhoneNumberUpdateRequest = components["schemas"]["PhoneNumberUpdateRequest"];
export type PhoneNumberHealth = components["schemas"]["PhoneNumberHealthResponse"];

export type JobAccepted = components["schemas"]["JobAcceptedResponse"];

/**
 * WABA status — the three values `ck_waba_status` permits (Doc 03 §5.1).
 *
 * The contract types the field as `str`, so these are the **display vocabulary**, not an API type.
 * A value outside the list renders verbatim rather than being dropped.
 *
 * Note what is *not* here: there is no verification field on a WABA. Meta's business-verification
 * state is not stored, so the platform can only report what it holds — the account's own status and
 * whether its credential is present and unexpired.
 */
export const WABA_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  suspended: "Suspended",
  disabled: "Disabled",
};

export const WABA_STATUSES = Object.keys(WABA_STATUS_LABELS);

export const WABA_STATUS_EXPLANATIONS: Record<string, string> = {
  active: "Connected and usable. Templates and campaigns on this account can send.",
  suspended: "Temporarily stopped. Nothing sends until it is set back to active.",
  disabled: "Switched off. Nothing sends, and it stays that way until it is re-enabled.",
};

/** Meta's quality buckets for a number (`ck_phone_quality`). Upper case on the wire. */
export const QUALITY_RATINGS = ["GREEN", "YELLOW", "RED"];

export const QUALITY_EXPLANATIONS: Record<string, string> = {
  GREEN: "High quality. No delivery restrictions from Meta.",
  YELLOW: "Quality has dipped. Meta is watching this number — reduce low-value sends.",
  RED: "Low quality. Meta may restrict or downgrade this number's messaging limit.",
};

/**
 * A number's `status` is a free `String(32)` with no check constraint — whatever Meta's sync
 * writes lands there, and only `"connected"` is known to the platform (it is both the column
 * default and what the health check tests for). Filter options are therefore derived from the
 * numbers actually loaded rather than from a list that would go stale.
 */
export const NUMBER_STATUS_CONNECTED = "connected";

/**
 * Whether a token exists and is still in date.
 *
 * `token_set` says only that a credential is stored — an expired one is stored too, and would fail
 * at the next Meta call. Reporting them separately is what makes the difference visible before a
 * send fails rather than after.
 */
export type TokenState = "missing" | "expired" | "expiring" | "ok";

/** Inside this window an operator should rotate before it lapses. */
export const TOKEN_EXPIRY_WARNING_DAYS = 14;

export function tokenState(waba: Waba, now: number = Date.now()): TokenState {
  if (!waba.token_set) return "missing";
  if (!waba.token_expires_at) return "ok";
  const expiresAt = Date.parse(waba.token_expires_at);
  if (Number.isNaN(expiresAt)) return "ok";
  if (expiresAt <= now) return "expired";
  return expiresAt - now <= TOKEN_EXPIRY_WARNING_DAYS * 86_400_000 ? "expiring" : "ok";
}

export const TOKEN_STATE_LABELS: Record<TokenState, string> = {
  missing: "No token",
  expired: "Token expired",
  expiring: "Token expiring",
  ok: "Token set",
};

// --- Lifecycle rules, mirrored from the server so the UI offers only what will be accepted ------

/** Only an account with no numbers may be disconnected — the server answers 409 otherwise. */
export function isDisconnectable(waba: Waba): boolean {
  return waba.phone_number_count === 0;
}

/** A suspended or disabled account can be set back to active; an active one has nowhere to go. */
export function isReactivatable(waba: Waba): boolean {
  return waba.status !== "active";
}

/** A number is usable when it is connected and Meta has not marked it red. */
export function isNumberHealthy(number: PhoneNumber): boolean {
  return number.status === NUMBER_STATUS_CONNECTED && number.quality_rating !== "RED";
}

// --- List queries (client-side; see `api.ts` for why) --------------------------------------------

export type WabaSort = "name" | "-name" | "-created_at" | "-numbers";

export interface WabaListQuery {
  q: string;
  status: string;
  sort: WabaSort;
}

export const DEFAULT_WABA_QUERY: WabaListQuery = { q: "", status: "", sort: "name" };

export type NumberSort = "number" | "-number" | "-quality" | "-mps_limit";

export interface NumberListQuery {
  q: string;
  waba: string;
  status: string;
  quality: string;
  sort: NumberSort;
}

export const DEFAULT_NUMBER_QUERY: NumberListQuery = {
  q: "",
  waba: "",
  status: "",
  quality: "",
  sort: "number",
};
