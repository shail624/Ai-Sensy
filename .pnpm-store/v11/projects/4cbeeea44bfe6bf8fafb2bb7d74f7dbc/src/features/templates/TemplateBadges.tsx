import type { Category } from "@/features/templates/types";
import { CATEGORY_LABELS, STATUS_LABELS } from "@/features/templates/types";

/**
 * Approval status → chip tone. Only `approved` is green: a template in any other state cannot be
 * broadcast, and colouring `pending` as success would misread the one thing this badge is for.
 */
const STATUS_TONE: Record<string, string> = {
  draft: "border-border text-text-secondary",
  pending: "border-info text-info",
  approved: "border-success text-success",
  rejected: "border-danger text-danger",
  paused: "border-warning text-warning",
  disabled: "border-border text-text-disabled",
};

/** Meta's template quality signal, as it names the buckets. */
const QUALITY_TONE: Record<string, string> = {
  green: "border-success text-success",
  high: "border-success text-success",
  yellow: "border-warning text-warning",
  medium: "border-warning text-warning",
  red: "border-danger text-danger",
  low: "border-danger text-danger",
  unknown: "border-border text-text-disabled",
};

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function TemplateStatusChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip(STATUS_TONE[value] ?? "border-border text-text-primary")}>
      {STATUS_LABELS[value] ?? value}
    </span>
  );
}

export function CategoryChip({ value }: { value: string }): JSX.Element {
  return (
    <span className={chip("border-border text-text-secondary")}>
      {CATEGORY_LABELS[value as Category] ?? value}
    </span>
  );
}

export function LanguageChip({ value }: { value: string }): JSX.Element {
  return <span className={chip("border-border text-text-secondary font-mono")}>{value}</span>;
}

/**
 * Meta's quality rating. Absent means Meta has not rated it yet — which is not the same as a bad
 * rating, so it renders as "not rated" rather than an empty or red chip.
 */
export function QualityChip({ value }: { value: string | null | undefined }): JSX.Element {
  if (!value) {
    return <span className={chip("border-border text-text-disabled")}>Not rated</span>;
  }
  return (
    <span className={chip(QUALITY_TONE[value.toLowerCase()] ?? "border-border text-text-primary")}>
      Quality: {value}
    </span>
  );
}

/** The one question a campaign author asks: can this be broadcast right now? */
export function SendableMarker({ sendable }: { sendable: boolean }): JSX.Element {
  return sendable ? (
    <span className={chip("border-success text-success")}>Sendable</span>
  ) : (
    <span className={chip("border-border text-text-disabled")}>Not sendable</span>
  );
}
