import type { TokenState, Waba } from "@/features/channels/types";
import {
  QUALITY_EXPLANATIONS,
  TOKEN_STATE_LABELS,
  tokenState,
  WABA_STATUS_LABELS,
} from "@/features/channels/types";

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

const WABA_TONE: Record<string, string> = {
  active: "border-success text-success",
  suspended: "border-warning text-warning",
  disabled: "border-border text-text-disabled",
};

export function WabaStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(WABA_TONE[value] ?? "border-border text-text-primary")}>
      {WABA_STATUS_LABELS[value] ?? value}
    </span>
  );
}

const TOKEN_TONE: Record<TokenState, string> = {
  missing: "border-danger text-danger",
  expired: "border-danger text-danger",
  expiring: "border-warning text-warning",
  ok: "border-success text-success",
};

/**
 * Credential health.
 *
 * The token itself is never returned — `token_set` says only that one exists — so this reports the
 * two things the platform *can* know: whether a credential is stored, and whether its recorded
 * expiry has passed or is close. An expired token is stored too, and would fail at the next Meta
 * call, which is exactly why "set" and "usable" are not the same badge.
 */
export function TokenChip({ waba }: { waba: Waba }): JSX.Element {
  const state = tokenState(waba);
  return <span className={chip(TOKEN_TONE[state])}>{TOKEN_STATE_LABELS[state]}</span>;
}

const QUALITY_TONE: Record<string, string> = {
  GREEN: "border-success text-success",
  YELLOW: "border-warning text-warning",
  RED: "border-danger text-danger",
};

/**
 * Meta's quality rating. Absent means Meta has not rated the number yet — not that it is bad — so
 * it reads as "not rated" rather than as an empty or red chip.
 */
export function QualityChip({ value }: { value: string | null | undefined }): JSX.Element {
  if (!value) {
    return <span className={chip("border-border text-text-disabled")}>Not rated</span>;
  }
  return (
    <span
      title={QUALITY_EXPLANATIONS[value]}
      className={chip(QUALITY_TONE[value] ?? "border-border text-text-primary")}
    >
      {value}
    </span>
  );
}

/** A number's connection status. Only `connected` is known to the platform; the rest pass through. */
export function NumberStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span
      className={chip(
        value === "connected" ? "border-success text-success" : "border-warning text-warning",
      )}
    >
      {value}
    </span>
  );
}

/** The one number a send falls back to when a campaign names none. */
export function DefaultChip(): JSX.Element {
  return <span className={chip("border-info text-info")}>Default</span>;
}

/** The health endpoint's own verdict: connected, and not rated RED. */
export function HealthChip({ healthy }: { healthy: boolean }): JSX.Element {
  return (
    <span className={chip(healthy ? "border-success text-success" : "border-danger text-danger")}>
      {healthy ? "Healthy" : "Needs attention"}
    </span>
  );
}

/** A plain value chip for the free-form Meta strings — tier and throughput carry no vocabulary. */
export function MetaValueChip({ value }: { value: string | null | undefined }): JSX.Element {
  if (!value) return <span className="text-text-disabled">—</span>;
  return <span className={chip("border-border font-mono text-text-secondary")}>{value}</span>;
}
