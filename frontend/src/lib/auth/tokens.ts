/**
 * Session token store (Doc 02 Phase 2 · Doc 04 §11).
 *
 * **Storage policy.** The *access* token lives in module memory only — never in
 * `localStorage`/`sessionStorage` — so a successful XSS cannot read it out of persistent storage,
 * and it dies with the tab. The *refresh* token is persisted, because the backend's refresh grant is
 * a request-body flow (`POST /auth/refresh`) rather than an httpOnly cookie, and without persistence
 * every page reload would sign the user out.
 *
 * That is a deliberate, documented trade-off, not an oversight: the refresh token is the weaker
 * secret (single-use, rotated on every exchange with reuse detection — Doc 04 §11), while the
 * access token is the one presented on every call. Moving refresh into an httpOnly cookie is a
 * backend change and is recorded as follow-up work.
 */

const REFRESH_KEY = "wa.auth.refresh";

let accessToken: string | null = null;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

/** Subscribe to sign-in/sign-out transitions (used to reset cached query data). */
export function onSessionChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

/** Persist a freshly issued token pair. */
export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  if (typeof localStorage !== "undefined") localStorage.setItem(REFRESH_KEY, refresh);
  notify();
}

export function clearTokens(): void {
  accessToken = null;
  if (typeof localStorage !== "undefined") localStorage.removeItem(REFRESH_KEY);
  notify();
}

/** Whether a session can plausibly be restored — a refresh token survived the reload. */
export function hasPersistedSession(): boolean {
  return getRefreshToken() !== null;
}
