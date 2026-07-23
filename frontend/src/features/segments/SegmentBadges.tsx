import type { MatchType, Segment } from "@/features/segments/types";
import { isStale, MATCH_TYPE_EXPLANATIONS, MATCH_TYPE_LABELS } from "@/features/segments/types";
import { formatCount } from "@/lib/format";

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function MatchTypeChip({ value }: { value: string }): JSX.Element {
  return (
    <span
      title={MATCH_TYPE_EXPLANATIONS[value as MatchType]}
      className={chip("border-border text-text-secondary")}
    >
      {MATCH_TYPE_LABELS[value as MatchType] ?? value}
    </span>
  );
}

/**
 * The segment's size.
 *
 * A segment whose rules changed since it was last evaluated has **no** count — the server resets it
 * to null rather than leaving a stale number — so "not evaluated" is rendered as its own state.
 * Showing it as `0` would claim the segment matches nobody, which is a different and much more
 * dangerous statement to make before a campaign.
 */
export function CountChip({ segment }: { segment: Segment }): JSX.Element {
  if (isStale(segment)) {
    return (
      <span
        title="The rules changed since this was last evaluated. Refresh to recompute the size."
        className={chip("border-warning text-warning")}
      >
        Not evaluated
      </span>
    );
  }
  const count = segment.cached_count ?? 0;
  return (
    <span
      className={chip(count === 0 ? "border-border text-text-disabled" : "border-success text-success")}
    >
      {formatCount(count)} contact{count === 1 ? "" : "s"}
    </span>
  );
}

/** Every segment the platform creates is dynamic; the flag is shown where it is part of the record. */
export function DynamicChip({ dynamic }: { dynamic: boolean }): JSX.Element {
  return (
    <span
      title={
        dynamic
          ? "Evaluated live against the contact list every time it is used."
          : "A fixed list rather than a live filter."
      }
      className={chip(dynamic ? "border-info text-info" : "border-border text-text-secondary")}
    >
      {dynamic ? "Dynamic" : "Static"}
    </span>
  );
}

export function RuleCountChip({ count }: { count: number }): JSX.Element {
  if (count === 0) {
    return (
      <span
        title="A segment with no conditions matches every contact."
        className={chip("border-warning text-warning")}
      >
        No conditions
      </span>
    );
  }
  return (
    <span className={chip("border-border text-text-secondary")}>
      {count} condition{count === 1 ? "" : "s"}
    </span>
  );
}
