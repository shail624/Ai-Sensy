/** A `{ data?, error? }` result from the openapi-fetch client. */
interface FetchResult<T> {
  data?: T;
  error?: unknown;
}

/** Turn an openapi-fetch result into data-or-throw, so React Query owns the error path. */
export function unwrap<T>(result: FetchResult<T>): T {
  if (result.error !== undefined) throw result.error;
  if (result.data === undefined) throw new Error("The server returned an empty response.");
  return result.data;
}

/** Human-readable message from an RFC 7807 problem body (Doc 04 §5) or any thrown value. */
export function apiErrorMessage(error: unknown): string {
  if (error && typeof error === "object") {
    const body = error as { detail?: unknown; title?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (typeof body.title === "string") return body.title;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}
