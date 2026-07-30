import {
  Activity,
  ArrowRight,
  History,
  MessageCircleMore,
  UserRoundPlus,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  AUDIENCE_PRESETS,
  type AudiencePresetId,
} from "@/features/segments/audiencePresets";
import { useHasPermission } from "@/features/segments/api";

const ICONS = {
  recently_engaged: MessageCircleMore,
  reactivation_ready: History,
  new_contacts: UserRoundPlus,
  whatsapp_active: Activity,
} satisfies Record<AudiencePresetId, typeof Activity>;

/** Compact entry points into the normal segment editor; no audience is created implicitly. */
export function AudiencePresetGallery(): JSX.Element | null {
  const canWrite = useHasPermission("segments:write");
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
        <p className="text-xs text-text-disabled">Dates are fixed when the segment is created.</p>
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
    </section>
  );
}
