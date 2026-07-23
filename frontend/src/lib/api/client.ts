import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "@/lib/api/schema";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/tokens";

/**
 * Typed API client, bound to the frozen OpenAPI contract (`frontend/openapi.json`).
 *
 * Paths in the spec already carry the `/api/v1` prefix, so the base URL is the origin only
 * (empty string = same-origin). In local dev the Vite server proxies `/api` to the backend
 * (see `vite.config.ts`); set `VITE_API_BASE_URL` for non-proxied deployments.
 *
 * Endpoints and request/response models are **never** hand-written — regenerate the types from the
 * spec with `npm run gen:api`.
 */
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Resolve `fetch` at call time rather than letting the client capture it at construction. The
 * behaviour is identical in the browser, and it keeps the transport swappable under test.
 */
const clientFetch: typeof fetch = (input, init) => globalThis.fetch(input, init);

/**
 * A bare client for the credential endpoints themselves (login/refresh). It carries **no**
 * middleware, so refreshing a token cannot recurse back into the 401 handler below. Same generated
 * `paths` type — a second client, not a second contract.
 */
export const authClient = createClient<paths>({ baseUrl, fetch: clientFetch });

export const api = createClient<paths>({ baseUrl, fetch: clientFetch });

/** Paths that must never carry a bearer token nor trigger a refresh attempt. */
const CREDENTIAL_PATHS = new Set(["/api/v1/auth/login", "/api/v1/auth/refresh"]);

/** Set by the auth provider so an unrecoverable session can route the app to /login. */
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

/**
 * Single-flight refresh: concurrent 401s share one `/auth/refresh` exchange. Without this, a page
 * that fires several queries at once would spend several refresh tokens, and the backend's
 * rotation/reuse detection (Doc 04 §11) would correctly revoke the whole session.
 */
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;

  const { data } = await authClient.POST("/api/v1/auth/refresh", { body: { refresh_token } });
  if (!data) {
    clearTokens();
    return false;
  }
  setTokens(data.access_token, data.refresh_token);
  return true;
}

export function refreshOnce(): Promise<boolean> {
  refreshInFlight ??= refreshSession()
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

const authMiddleware: Middleware = {
  onRequest({ request, schemaPath }) {
    if (CREDENTIAL_PATHS.has(schemaPath)) return undefined;
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },

  async onResponse({ request, response, schemaPath }) {
    if (response.status !== 401 || CREDENTIAL_PATHS.has(schemaPath)) return undefined;

    // The access token expired (or the tab reloaded into a cold memory store). Exchange the
    // refresh token once, then replay the original request; a failed exchange ends the session.
    const retryRequest = request.clone();
    const refreshed = await refreshOnce();
    if (!refreshed) {
      clearTokens();
      onSessionExpired?.();
      return undefined;
    }

    retryRequest.headers.set("Authorization", `Bearer ${getAccessToken() ?? ""}`);
    return globalThis.fetch(retryRequest);
  },
};

api.use(authMiddleware);

export type { paths } from "@/lib/api/schema";
