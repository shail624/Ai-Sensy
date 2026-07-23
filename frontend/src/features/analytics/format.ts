import type { KpiKind } from "@/features/analytics/types";

/** Shown wherever the API returned `null` — the value is *unknown*, not zero (Doc 15 §11). */
export const UNKNOWN = "—";

export function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return UNKNOWN;
  return `${(value * 100).toFixed(1)}%`;
}

/** Durations arrive in seconds, except delivery latency which is milliseconds. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return UNKNOWN;
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

/** Cost is stored in micro-units of the organization's currency (Doc 15 §9.1). */
export function formatMicros(micros: number | null | undefined): string {
  if (micros === null || micros === undefined) return UNKNOWN;
  return (micros / 1_000_000).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return UNKNOWN;
  return value.toLocaleString();
}

export function formatKpi(value: number | null | undefined, kind: KpiKind): string {
  if (kind === "rate") return formatRate(value);
  if (kind === "micros") return formatMicros(value);
  if (kind === "duration") return formatDuration(value);
  return formatCount(value);
}

/** Relative age of the rollup watermark, for the freshness indicator (Doc 15 §22). */
export function formatLag(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "never run";
  if (seconds < 90) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86_400)} d ago`;
}

/** A percentage delta between a current and previous value, or null when it cannot be computed. */
export function delta(current: number | null | undefined, previous: number | null | undefined): number | null {
  if (current === null || current === undefined) return null;
  if (previous === null || previous === undefined || previous === 0) return null;
  return (current - previous) / previous;
}
