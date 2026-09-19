import { Link } from "react-router-dom";

import { Badge, type BadgeTone, ErrorState, Skeleton } from "@/components/ui";
import { useNumbers } from "@/features/channels/api";
import { NUMBER_STATUS_CONNECTED, type PhoneNumber } from "@/features/channels/types";
import { apiErrorMessage } from "@/lib/api/errors";

const QUALITY_TONES: Record<string, BadgeTone> = {
  GREEN: "success",
  YELLOW: "warning",
  RED: "danger",
};

/** Meta's own words are shouted; an operator reads a sentence faster than an enum. */
const QUALITY_LABELS: Record<string, string> = {
  GREEN: "Good standing",
  YELLOW: "Quality slipping",
  RED: "Quality flagged",
};

function qualityTone(number: PhoneNumber): BadgeTone {
  if (number.status !== NUMBER_STATUS_CONNECTED) return "danger";
  return QUALITY_TONES[number.quality_rating ?? ""] ?? "neutral";
}

function qualityLabel(number: PhoneNumber): string {
  if (number.status !== NUMBER_STATUS_CONNECTED) return number.status;
  return QUALITY_LABELS[number.quality_rating ?? ""] ?? "Not rated yet";
}

/**
 * Meta's own words for what a tier permits, rather than the raw enum.
 *
 * The number is the one an operator needs before scheduling a campaign, and it is the part the
 * enum name hides: `TIER_10K` says nothing about how many messages tomorrow's send may contain.
 */
const TIER_LABELS: Record<string, string> = {
  TIER_50: "50 customers / 24h",
  TIER_250: "250 customers / 24h",
  TIER_1K: "1,000 customers / 24h",
  TIER_10K: "10,000 customers / 24h",
  TIER_100K: "100,000 customers / 24h",
  TIER_UNLIMITED: "Unlimited",
};

function since(value: string | null | undefined): string {
  if (!value) return "never checked";
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60_000);
  if (minutes < 2) return "checked just now";
  if (minutes < 60) return `checked ${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `checked ${hours}h ago`;
  return `checked ${Math.round(hours / 24)} days ago`;
}

/**
 * Whether WhatsApp will accept sends, on the screen an operator opens first.
 *
 * Every field here was already stored and already synced; nothing about it was reachable without
 * navigating to Channels, so a number flagged RED overnight stayed invisible until a campaign
 * failed. Sending capacity is a precondition for most of the work below it on this page, which is
 * why it sits at the top rather than in a settings screen.
 *
 * It states when each number was last checked, because these values are what the **last sync**
 * wrote rather than a live call to Meta. A green badge with no timestamp would be read as "fine
 * now" when it may mean "fine on Tuesday" — and the whole point of the strip is to be trusted.
 */
export function ChannelHealthStrip(): JSX.Element | null {
  const numbers = useNumbers();

  if (numbers.isPending) return <Skeleton className="h-16 w-full rounded-control" />;
  if (numbers.isError) {
    return (
      <ErrorState
        message={`WhatsApp sending status is unavailable. ${apiErrorMessage(numbers.error)}`}
        onRetry={() => void numbers.refetch()}
      />
    );
  }

  const rows = numbers.data ?? [];
  if (rows.length === 0) {
    return (
      <div className="rounded-control border border-border bg-surface-2 px-3 py-2.5 text-xs text-text-secondary">
        No WhatsApp number is connected yet, so nothing can be sent.{" "}
        <Link to="/channels/accounts" className="font-semibold text-accent hover:underline">
          Connect a number
        </Link>
        .
      </div>
    );
  }

  // Worst first: the number that will stop a send is the one worth reading, and on a wide account
  // the healthy ones would otherwise push it off the end of the row.
  const ordered = [...rows].sort(
    (left, right) => severity(right) - severity(left) || left.display_number.localeCompare(right.display_number),
  );

  return (
    <section
      aria-label="WhatsApp sending status"
      className="rounded-control border border-border bg-surface-2 px-3 py-2.5"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p className="text-xs font-semibold text-text-primary">WhatsApp sending</p>
        <ul className="flex flex-1 flex-wrap items-center gap-x-4 gap-y-2">
          {ordered.map((number) => (
            <li key={number.id} className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-text-primary">{number.display_number}</span>
              <Badge tone={qualityTone(number)}>{qualityLabel(number)}</Badge>
              {number.messaging_tier ? (
                <span className="text-xs text-text-secondary">
                  {TIER_LABELS[number.messaging_tier] ?? number.messaging_tier}
                </span>
              ) : null}
              <span className="text-xs text-text-disabled">{since(number.last_synced_at)}</span>
            </li>
          ))}
        </ul>
        <Link
          to="/channels/numbers"
          className="text-xs font-semibold text-accent hover:underline"
        >
          Manage numbers
        </Link>
      </div>
    </section>
  );
}

/** Higher is more urgent, so the sort reads worst-first without a second comparator. */
function severity(number: PhoneNumber): number {
  if (number.status !== NUMBER_STATUS_CONNECTED) return 3;
  if (number.quality_rating === "RED") return 2;
  if (number.quality_rating === "YELLOW") return 1;
  return 0;
}
