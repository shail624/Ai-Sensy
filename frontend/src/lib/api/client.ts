import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

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
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? "",
});

export type { paths } from "@/lib/api/schema";
