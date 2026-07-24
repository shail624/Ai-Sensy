import { Badge } from "@/components/ui";
import type { MatchType, Segment } from "@/features/segments/types";
import { isStale, MATCH_TYPE_EXPLANATIONS, MATCH_TYPE_LABELS } from "@/features/segments/types";
import { formatCount } from "@/lib/format";

export function MatchTypeChip({ value }: { value: string }): JSX.Element {
  return (
    <Badge tone="neutral" title={MATCH_TYPE_EXPLANATIONS[value as MatchType]}>
      {MATCH_TYPE_LABELS[value as MatchType] ?? value}
    </Badge>
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
      <Badge
        tone="warning"
        dot
        title="The rules changed since this was last evaluated. Refresh to recompute the size."
      >
        Not evaluated
      </Badge>
    );
  }
  const count = segment.cached_count ?? 0;
  return (
    <Badge tone={count === 0 ? "neutral" : "success"} dot>
      {formatCount(count)} contact{count === 1 ? "" : "s"}
    </Badge>
  );
}

/** Every segment the platform creates is dynamic; the flag is shown where it is part of the record. */
export function DynamicChip({ dynamic }: { dynamic: boolean }): JSX.Element {
  return (
    <Badge
      tone={dynamic ? "info" : "neutral"}
      title={
        dynamic
          ? "Evaluated live against the contact list every time it is used."
          : "A fixed list rather than a live filter."
      }
    >
      {dynamic ? "Dynamic" : "Static"}
    </Badge>
  );
}

export function RuleCountChip({ count }: { count: number }): JSX.Element {
  if (count === 0) {
    return (
      <Badge tone="warning" title="A segment with no conditions matches every contact.">
        No conditions
      </Badge>
    );
  }
  return (
    <Badge tone="neutral">
      {count} condition{count === 1 ? "" : "s"}
    </Badge>
  );
}
