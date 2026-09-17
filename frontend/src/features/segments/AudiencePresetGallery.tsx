import {
  Activity,
  ArrowRight,
  History,
  MessageCircleMore,
  Users,
  UserRoundPlus,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  AUDIENCE_PRESETS,
  type AudiencePresetId,
} from "@/features/segments/audiencePresets";
import { useHasPermission, useSegments } from "@/features/segments/api";
import type { Segment } from "@/features/segments/types";

const ICONS = {
  recently_engaged: MessageCircleMore,
  reactivation_ready: History,
  reactivation_eligible: Activity,
  kyc_pending: History,
  interested_customers: UserRoundPlus,
  documents_pending: History,
  activation_pending: Activity,
  completed_customers: Activity,
  new_contacts: UserRoundPlus,
  whatsapp_active: Activity,
  whatsapp_reachable: MessageCircleMore,
  whatsapp_unreachable: MessageCircleMore,
} satisfies Record<AudiencePresetId, typeof Activity>;

//: How many of the team's own audiences to offer beside the built-in ones. Enough to be useful,
//: few enough that the built-ins are still visible above the fold; the rest are one link away in
//: the list this page already shows.
const TEAM_STARTERS = 4;

/** Compact entry points into the normal segment editor; no audience is created implicitly. */
export function AudiencePresetGallery(): JSX.Element | null {
  const canWrite = useHasPermission("segments:write");
  // Already fetched for the list on this page, so this is the cache, not a second request.
  const segments = useSegments();
  const mine = [...(segments.data ?? [])]
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .slice(0, TEAM_STARTERS);
  if (!canWrite) return null;

  return (
    <section
      aria-labelledby="audience-presets-title"
      className="mb-5 rounded-2xl border border-border bg-surface p-4 shadow-sm"
    >
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="audience-presets-title" className="text-base font-semibold text-text-primary">
            Quick-start audiences
          </h2>
          <p className="mt-0.5 text-sm text-text-secondary">
            Start with a common audience, review its condition, then save it for campaigns.
          </p>
        </div>
        <p className="text-xs text-text-disabled">
          Date-based presets keep their visible cutoff when created.
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {AUDIENCE_PRESETS.map((preset) => {
          const Icon = ICONS[preset.id];
          return (
            <Link
              key={preset.id}
              to="/segments/new"
              state={{ audiencePresetId: preset.id }}
              className="group flex min-h-28 items-start gap-3 rounded-xl border border-border bg-surface-subtle p-3 transition hover:border-accent hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-accent shadow-sm">
                <Icon aria-hidden className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2 text-sm font-semibold text-text-primary">
                  {preset.label}
                  <ArrowRight
                    aria-hidden
                    className="h-4 w-4 shrink-0 text-text-disabled transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                  />
                </span>
                <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                  {preset.description}
                </span>
                <span className="mt-2 block text-[11px] font-semibold uppercase tracking-wide text-accent">
                  {preset.window}
                </span>
              </span>
            </Link>
          );
        })}
      </div>

      {mine.length > 0 ? <TeamStarters segments={mine} /> : null}
    </section>
  );
}

/**
 * The audiences this team has already built, offered as starting points.
 *
 * Every segment is visible to the whole organization -- there is no private/shared distinction on
 * the model -- and any of them can already be copied from the list's Duplicate action. What was
 * missing was only that somebody building their first audience never saw them: the quick-start
 * gallery showed the ten built-in recipes and nothing the team itself had written, so the work
 * colleagues had already done was discoverable only if you knew where to look.
 *
 * The link carries the same `duplicateOf` state the Duplicate action uses, so this adds an entry
 * point and no second copy path.
 */
function TeamStarters({ segments }: { segments: Segment[] }): JSX.Element {
  return (
    <div className="mt-4 border-t border-border pt-4">
      <h3 className="text-sm font-semibold text-text-primary">Start from your team&rsquo;s audiences</h3>
      <p className="mt-0.5 text-sm text-text-secondary">
        A copy opens in the editor with a new name. The original is left alone.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {segments.map((segment) => (
          <Link
            key={segment.id}
            to="/segments/new"
            state={{ duplicateOf: segment }}
            className="group flex min-h-20 items-start gap-3 rounded-xl border border-border bg-surface-subtle p-3 transition hover:border-accent hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-accent shadow-sm">
              <Users aria-hidden className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center justify-between gap-2 text-sm font-semibold text-text-primary">
                <span className="truncate">{segment.name}</span>
                <ArrowRight
                  aria-hidden
                  className="h-4 w-4 shrink-0 text-text-disabled transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                />
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                {segment.description || `${segment.rules.length} condition${segment.rules.length === 1 ? "" : "s"}`}
              </span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
