/**
 * Shared presentation formatters.
 *
 * Formatting only — no business logic, no rounding decisions that change meaning. The discipline
 * these share is that `null`/`undefined` mean *unknown*, not zero, and render as a dash: a blank or
 * a `0` would assert something the server never said.
 *
 * Domain-specific formatting stays with its feature — analytics' micro-unit money and campaigns'
 * fixed-scale decimal money are different representations and must not be conflated.
 */

export const UNKNOWN = "—";

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return UNKNOWN;
  return value.toLocaleString();
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? UNKNOWN : parsed.toLocaleString();
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? UNKNOWN : parsed.toLocaleDateString();
}

/**
 * A byte count in the units people read.
 *
 * Binary units (1 KB = 1024 B), because that is what the platform's own limits are expressed in —
 * a 5 MB image ceiling is 5 × 1024 × 1024 bytes, and rendering it as "5.2 MB" would make a file at
 * the limit look over it.
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return UNKNOWN;
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  // One decimal until the number is big enough not to need it — "1.5 KB" is useful, "512.0 MB"
  // is noise.
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
}

/** A whole-second duration as `m:ss`, or `h:mm:ss` once it passes an hour. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return UNKNOWN;
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${minutes}:${pad(secs)}`;
}

/** Relative age, for "last synced" style captions. */
export function formatAge(iso: string | null | undefined): string {
  if (!iso) return "never";
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return UNKNOWN;
  const seconds = Math.max(0, (Date.now() - parsed) / 1000);
  if (seconds < 90) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86_400)} d ago`;
}
