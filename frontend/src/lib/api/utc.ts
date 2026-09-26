import type { Middleware } from "openapi-fetch";

/**
 * The API stores and returns every timestamp as naive UTC (`2026-09-24T01:02:49.471787`, no
 * offset — Doc 03 §1.3). `new Date()` reads an offset-less date-time as *local* time, which put
 * every time in India 5h30m behind ("6h waiting" for a message that just arrived). Marking those
 * strings as UTC once, at the client, fixes every screen without touching 75 call sites.
 *
 * Only full date-times without an offset are changed. Plain dates (`2026-09-24`), clock times
 * (`10:30`) and values that already carry `Z` or `+05:30` are left exactly as they are.
 */
const NAIVE_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?$/;

export function markUtc(value: unknown): unknown {
  if (typeof value === "string") return NAIVE_DATETIME.test(value) ? `${value}Z` : value;
  if (Array.isArray(value)) return value.map(markUtc);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, markUtc(entry)]));
  }
  return value;
}

export const utcMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!(response.headers.get("content-type") ?? "").includes("application/json")) return undefined;
    const text = await response.clone().text();
    if (!text) return undefined;
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      return undefined;
    }
    const headers = new Headers(response.headers);
    headers.delete("content-length");
    return new Response(JSON.stringify(markUtc(body)), {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
